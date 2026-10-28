#include "burst_controller.h"
#include <iostream>
#include <thread>
#include <chrono>
#include <cstring>
#include <uhd/exception.hpp>

BurstController::BurstController(UsrpController&          usrp,
                                 std::vector<BandConfig>& bands,
                                 std::vector<TcpServer*>& servers)
    : usrp_(usrp), bands_(bands), servers_(servers)
{
    sample_buf_.reserve(SAMPLES_PER_CHUNK);
}

void BurstController::run()
{
    running_ = true;
    int cycle = 0;

    std::cout << "\n[BURST] ════════════════════════════════════════════\n";
    std::cout << "[BURST]  Burst cycle starting\n";
    double cycle_len = 0.0;
    for (const auto& band : bands_) {
        std::cout << "[BURST]  " << band.name << " : dwell " << band.dwell_sec
                  << "s, gap " << band.gap_sec << "s\n";
        cycle_len += band.dwell_sec + band.gap_sec;
    }
    // Print the duty cycle explicitly: with N bands each one only gets
    // dwell/cycle_len of wall-clock time, and that share is easy to lose track
    // of once bands are added.
    std::cout << "[BURST]  Cycle : " << cycle_len << "s total\n";
    for (const auto& band : bands_)
        std::cout << "[BURST]  " << band.name << " duty = "
                  << (100.0 * band.dwell_sec / cycle_len) << "%\n";
    std::cout << "[BURST] ════════════════════════════════════════════\n\n";

    while (running_) {
        ++cycle;
        std::cout << "[BURST] ── Cycle #" << cycle << " ──────────────────────────\n";

        for (int i = 0; i < static_cast<int>(bands_.size()) && running_; ++i) {
            // A USB hiccup (uhd::io_error / LIBUSB_TRANSFER_OVERFLOW, e.g. ADS-B's
            // 2 MSps on a marginal link) used to escape here and std::terminate()
            // the whole process, killing AIS along with it. Drop that band's dwell
            // and move on; only repeated failures with NO good dwell in between
            // (a radio that is really gone) stop Module 1.
            try {
                do_dwell(i);
                if (!running_) break;
                do_gap(i);
                usb_errors_ = 0;
            } catch (const uhd::exception& e) {
                ++usb_errors_;
                std::cerr << "[BURST] USB/UHD error on band " << bands_[i].name
                          << " (" << usb_errors_ << "/5): " << e.what() << "\n";
                try { usrp_.stop_stream(); } catch (...) {}
                if (usb_errors_ >= 5) {
                    std::cerr << "[BURST] FATAL: radio keeps failing — put the B210 on a USB 3 port "
                                 "with a short USB 3 cable (no hub)\n";
                    running_ = false;
                    break;
                }
                std::this_thread::sleep_for(std::chrono::milliseconds(500));
            }
        }
    }

    usrp_.stop_stream();
    std::cout << "[BURST] Loop exited cleanly.\n";
}

void BurstController::stop()
{
    running_ = false;
}

// ─────────────────────────────────────────────────────────────────────────────
//  DWELL — tune USRP to band[i], stream IQ to TCP server for DWELL_SEC
// ─────────────────────────────────────────────────────────────────────────────
void BurstController::do_dwell(int idx)
{
    const BandConfig& band = bands_[idx];
    current_band_          = idx;

    std::cout << "[BURST] ▶ DWELL  band=" << band.name
              << "  freq=" << band.freq_hz / 1e6 << " MHz"
              << "  rate=" << band.samp_rate_hz / 1e3 << " kSps"
              << "  port=" << band.tcp_port << "\n";

    // ── Retune + rate ────────────────────────────────────────────────────────
    // Rate is set alongside frequency because the RX stream is already torn
    // down and rebuilt on every dwell transition regardless of band (see
    // start_stream() below) -- this rides that same rebuild rather than
    // adding a new one.
    usrp_.stop_stream();
    usrp_.set_rate(band.samp_rate_hz);
    bool locked = usrp_.tune(band.freq_hz);
    if (!locked) {
        std::cerr << "[BURST]   WARNING: LO not locked for " << band.name << "\n";
    }
    usrp_.start_stream();

    // ── Stream for band.dwell_sec ────────────────────────────────────────────
    const size_t chunk_samples = chunk_samples_for(band.samp_rate_hz);
    auto deadline = std::chrono::steady_clock::now()
                  + std::chrono::milliseconds(static_cast<int>(band.dwell_sec * 1000));

    size_t total_samples = 0;

    // Keep the OTHER bands' sockets fed with zero-fill for the full duration
    // of this dwell too (not just during do_gap()) — previously they received
    // nothing at all while a different band was active, which starved
    // whichever band wasn't currently tuned for up to the combined dwell time
    // of the other bands every cycle.
    static const std::vector<uint8_t> zero_chunk(
        SAMPLES_PER_CHUNK * sizeof(std::complex<float>), 0);

    while (running_ && std::chrono::steady_clock::now() < deadline) {
        int got = usrp_.stream(sample_buf_, chunk_samples);
        if (got <= 0) {
            std::cerr << "[BURST]   RX error, skipping chunk\n";
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
            continue;
        }

        // Send raw bytes to the matching TCP server
        const uint8_t* raw = reinterpret_cast<const uint8_t*>(sample_buf_.data());
        size_t         len = static_cast<size_t>(got) * sizeof(std::complex<float>);
        servers_[idx]->broadcast(raw, len);
        total_samples += static_cast<size_t>(got);

        // Keep-alive TRICKLE for the bands that are not tuned right now.
        //
        // This used to push a full-rate zero-fill chunk to every other band on
        // every iteration. At 8 bands that is 8 x 200 kSps x 8 B = 12.8 MB/s
        // leaving Module 1, of which 11.2 MB/s is zeros -- more than the
        // decoder can consume, so its socket buffers filled with stale zeros
        // and the REAL dwell samples were dropped to make room. The console
        // then showed nothing but -180 dBFS because every chunk it managed to
        // read was ancient zero-fill.
        //
        // The zeros only exist so an idle tcp_source is not left completely
        // starved; that needs a trickle, not real-time rate. One chunk per
        // band per ~100 ms is ~41 kB/s each instead of 1.6 MB/s.
        {
            auto now = std::chrono::steady_clock::now();
            if (now - last_keepalive_ >= std::chrono::milliseconds(100)) {
                last_keepalive_ = now;
                for (int j = 0; j < static_cast<int>(bands_.size()); ++j)
                    if (j != idx)
                        servers_[j]->broadcast(zero_chunk.data(), zero_chunk.size());
            }
        }
    }

    double kb = (total_samples * sizeof(std::complex<float>)) / 1024.0;
    std::cout << "[BURST]   Dwell done — sent " << total_samples
              << " samples (" << static_cast<int>(kb) << " KB) to port "
              << band.tcp_port << "\n";
}

// ─────────────────────────────────────────────────────────────────────────────
//  GAP — USRP silent, send zero-fill to keep Module 2 TCP clients alive
// ─────────────────────────────────────────────────────────────────────────────
void BurstController::do_gap(int idx)
{
    current_band_ = -1;
    usrp_.stop_stream();

    const double gap = bands_[idx].gap_sec;
    std::cout << "[BURST] ■ GAP    " << gap << "s after "
              << bands_[idx].name << "\n";

    // Zero-fill buffer — keeps GNU Radio TCP source blocks happy (no disconnect)
    static const std::vector<uint8_t> zero_chunk(
        SAMPLES_PER_CHUNK * sizeof(std::complex<float>), 0);

    auto deadline = std::chrono::steady_clock::now()
                  + std::chrono::milliseconds(static_cast<int>(gap * 1000));

    // Keep-alive trickle only (see do_dwell): a 10 ms flood to all 8 bands was
    // 12.8 MB/s of zeros, which is what buried the real samples.
    while (running_ && std::chrono::steady_clock::now() < deadline) {
        for (int i = 0; i < static_cast<int>(bands_.size()); ++i)
            servers_[i]->broadcast(zero_chunk.data(), zero_chunk.size());
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
}
