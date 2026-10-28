#include "usrp_controller.h"
#include <uhd/exception.hpp>
#include <uhd/utils/thread.hpp>
#include <algorithm>
#include <iostream>
#include <thread>
#include <chrono>
#include <cstdlib>
#include <cstring>

namespace {
// Reads SECURECOM_RX_GAIN_DB from the environment so gain can be tuned per
// test setup (e.g. close-range bench testing needs far less than 40 dB)
// without a rebuild. Falls back to UsrpController::DEFAULT_GAIN.
double resolve_rx_gain_db()
{
    if (const char* env = std::getenv("SECURECOM_RX_GAIN_DB")) {
        try {
            return std::stod(env);
        } catch (...) {
            std::cerr << "[USRP] WARNING: invalid SECURECOM_RX_GAIN_DB=\"" << env
                      << "\" — falling back to default gain\n";
        }
    }
    return UsrpController::DEFAULT_GAIN;
}
} // namespace

UsrpController::UsrpController(const std::string& device_args)
{
    std::cout << "[USRP] Opening device: \""
              << (device_args.empty() ? "auto" : device_args) << "\"\n";

    try {
        usrp = uhd::usrp::multi_usrp::make(device_args);
    } catch (const uhd::exception& e) {
        std::cerr << "[USRP] ERROR: Could not open device — " << e.what() << "\n";
        throw;
    }

    // ── Sample Rate — set HARDWARE rate directly to 200 kSps ────────────────
    // B210 / AD9361 internal DSP decimates from master clock with proper
    // anti-alias (CIC + HB) filters. No software decimation needed.
    usrp->set_rx_rate(OUT_SAMPLE_RATE);
    double actual_rate = usrp->get_rx_rate();
    current_rate_ = actual_rate;
    std::cout << "[USRP] RX rate requested : " << OUT_SAMPLE_RATE / 1e3
              << " kSps\n";
    std::cout << "[USRP] RX rate actual    : " << actual_rate / 1e3
              << " kSps";
    if (std::abs(actual_rate - OUT_SAMPLE_RATE) > 1000.0)
        std::cout << "  ⚠ WARNING: rate mismatch!";
    else
        std::cout << "  ✔ OK";
    std::cout << "\n";

    // ── Gain ─────────────────────────────────────────────────────────────────
    // Override with SECURECOM_RX_GAIN_DB=<value> for close-range bench testing
    // — 40 dB (the fixed default) is likely to saturate the ADC at short range.
    double gain_db = resolve_rx_gain_db();
    usrp->set_rx_gain(gain_db);
    std::cout << "[USRP] RX gain requested : " << gain_db << " dB"
              << (gain_db == DEFAULT_GAIN ? "  (default)" : "  (from SECURECOM_RX_GAIN_DB)")
              << "\n";
    std::cout << "[USRP] RX gain actual    : " << usrp->get_rx_gain() << " dB\n";

    // ── Antenna ───────────────────────────────────────────────────────────────
    usrp->set_rx_antenna("RX2");
    std::cout << "[USRP] Antenna: " << usrp->get_rx_antenna() << "\n";

    // ── Stream args: complex float ─────────────────────────────────────────
    stream_args_ = uhd::stream_args_t("fc32", "sc16");
    stream_args_.args["block_size"] = "4096";

    std::cout << "[USRP] Init OK — B210 ready\n";
}

UsrpController::~UsrpController()
{
    stop_stream();
}

void UsrpController::set_rate(double samp_rate_hz)
{
    if (samp_rate_hz == current_rate_) return;   // no-op: already at this rate

    usrp->set_rx_rate(samp_rate_hz);
    double actual_rate = usrp->get_rx_rate();
    current_rate_ = actual_rate;

    std::cout << "[USRP] RX rate requested : " << samp_rate_hz / 1e3 << " kSps\n";
    std::cout << "[USRP] RX rate actual    : " << actual_rate / 1e3 << " kSps";
    // B210's achievable rates are quantised by its master-clock/decimation
    // options, so a request near 2 MSps can legitimately land a few percent
    // off -- a fixed Hz threshold (fine at 200 kSps) would false-positive
    // here. Scale the tolerance with the requested rate instead.
    if (std::abs(actual_rate - samp_rate_hz) > std::max(1000.0, samp_rate_hz * 0.05))
        std::cout << "  ⚠ WARNING: rate mismatch!";
    else
        std::cout << "  ✔ OK";
    std::cout << "\n";
}

bool UsrpController::tune(double freq_hz)
{
    uhd::tune_request_t tune_req(freq_hz);
    uhd::tune_result_t  result = usrp->set_rx_freq(tune_req);

    std::cout << "[USRP] Tuning to " << freq_hz / 1e6 << " MHz ...\n";
    std::cout << "[USRP]   Target  : " << result.target_rf_freq / 1e6 << " MHz\n";
    std::cout << "[USRP]   Actual  : " << result.actual_rf_freq / 1e6 << " MHz\n";

    // Wait for PLL lock (up to 200 ms)
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(200);
    while (std::chrono::steady_clock::now() < deadline) {
        if (is_locked()) {
            std::cout << "[USRP]   LO Lock : OK\n";
            return true;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }

    std::cerr << "[USRP]   LO Lock : TIMEOUT — proceeding anyway\n";
    return false;
}

void UsrpController::start_stream()
{
    if (streaming_) return;

    rx_stream_ = usrp->get_rx_stream(stream_args_);

    uhd::stream_cmd_t cmd(uhd::stream_cmd_t::STREAM_MODE_START_CONTINUOUS);
    cmd.num_samps  = 0;
    cmd.stream_now = true;
    rx_stream_->issue_stream_cmd(cmd);
    streaming_ = true;
    std::cout << "[USRP] RX stream STARTED\n";
}

void UsrpController::stop_stream()
{
    if (!streaming_ || !rx_stream_) return;

    uhd::stream_cmd_t cmd(uhd::stream_cmd_t::STREAM_MODE_STOP_CONTINUOUS);
    rx_stream_->issue_stream_cmd(cmd);
    streaming_ = false;

    // Drain packets still in flight after STOP. Left in the USB pipe they hit the
    // NEXT dwell's fresh streamer and fail it with LIBUSB_TRANSFER_OVERFLOW (seen on
    // a USB 2.0 link; the terrestrial Module 1 has the same fix).
    std::vector<std::complex<float>> junk(4096);
    uhd::rx_metadata_t md;
    for (int i = 0; i < 200; ++i) {
        try {
            if (rx_stream_->recv(junk.data(), junk.size(), md, 0.05) == 0 &&
                md.error_code == uhd::rx_metadata_t::ERROR_CODE_TIMEOUT)
                break;
        } catch (const uhd::exception&) {
            // a bad packet during the drain is exactly what we are flushing
        }
    }
    std::cout << "[USRP] RX stream STOPPED\n";
}

int UsrpController::stream(std::vector<std::complex<float>>& buf, size_t num_samples)
{
    if (!streaming_ || !rx_stream_) return -1;

    buf.resize(num_samples);
    uhd::rx_metadata_t md;

    size_t got = rx_stream_->recv(buf.data(), num_samples, md, 3.0);

    if (md.error_code != uhd::rx_metadata_t::ERROR_CODE_NONE) {
        std::cerr << "[USRP] RX error: " << md.strerror() << "\n";
        return -1;
    }

    // Hardware already outputs at 200 kSps — no software decimation needed.
    buf.resize(got);
    return static_cast<int>(got);
}

double UsrpController::get_actual_freq() const
{
    return usrp->get_rx_freq();
}

double UsrpController::get_actual_gain() const
{
    return usrp->get_rx_gain();
}

bool UsrpController::is_locked() const
{
    return usrp->get_rx_sensor("lo_locked").to_bool();
}
