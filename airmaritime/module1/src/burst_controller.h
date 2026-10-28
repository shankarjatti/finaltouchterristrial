#pragma once
#include <chrono>
#include "usrp_controller.h"
#include "tcp_server.h"
#include <vector>
#include <atomic>
#include <memory>

// ─────────────────────────────────────────────────────────────────────────────
//  BurstController
//
//  Cycles through the configured bands in sequence, e.g.:
//    DMR446  → [dwell BandConfig::dwell_sec] → [gap BandConfig::gap_sec]
//    NXDN96  → [dwell BandConfig::dwell_sec] → [gap BandConfig::gap_sec]
//    P25     → [dwell BandConfig::dwell_sec] → [gap BandConfig::gap_sec]
//    repeat …
//
//  Dwell time is per-band (BandConfig::dwell_sec) rather than one shared
//  constant — a band under active live testing (e.g. DMR with a real radio)
//  can be given a much longer dwell than bands only exercised via recorded
//  IQ, without giving every band equal, always-on-equal airtime regardless
//  of what's actually being validated right now.
//
//  During dwell:  tunes USRP, streams IQ → feeds the matching TcpServer
//  During gap:    USRP silent, sends zero-fill to keep TCP clients connected
// ─────────────────────────────────────────────────────────────────────────────
class BurstController {
public:
    // NOTE: gap is now per-band (BandConfig::gap_sec, env-overridable via
    // SECURECOM_<BAND>_GAP_SEC). There is deliberately no shared GAP_SEC
    // constant any more -- one existed and was a compile-time value, which is
    // why the console's Gap control could not do anything.

    // samples_per_chunk: how many decimated samples per TCP write burst, at
    // the base 200 kSps rate. 200kSps / 100 = 10ms chunks.
    static constexpr size_t SAMPLES_PER_CHUNK = 2000;

    // Real dwell data is chunked by DURATION (CHUNK_MS), not a fixed sample
    // count -- at 200 kSps that's SAMPLES_PER_CHUNK exactly, but a band with
    // a wider rate (e.g. ADS-B at 2 MSps) needs a proportionally larger chunk
    // to keep the same ~10ms cadence. Without this, a wideband dwell would
    // call TcpServer::broadcast() 10x more often for no benefit -- see
    // do_dwell(). Keep-alive zero-fill (do_dwell/do_gap) stays at the fixed
    // SAMPLES_PER_CHUNK regardless of target band: it is a trickle to
    // prevent idle sockets, not real data, so it does not need to track any
    // particular band's real rate.
    static constexpr double CHUNK_MS = 10.0;
    static size_t chunk_samples_for(double samp_rate_hz) {
        return static_cast<size_t>(samp_rate_hz * CHUNK_MS / 1000.0);
    }

    BurstController(UsrpController&              usrp,
                    std::vector<BandConfig>&     bands,
                    std::vector<TcpServer*>&     servers);

    // Start the burst loop (blocking — run in its own thread)
    void run();

    // Signal the loop to stop cleanly
    void stop();

    // Return current band index (-1 = gap)
    int  current_band() const { return current_band_.load(); }
    bool failed() const { return usb_errors_ >= 5; }   // gave up on the radio

private:
    // rate-limits the zero-fill keep-alive sent to bands that are not the
    // currently tuned one (see do_dwell in the .cpp for why this matters)
    std::chrono::steady_clock::time_point last_keepalive_{};

    void do_dwell(int band_idx);
    void do_gap(int band_idx);

    UsrpController&          usrp_;
    std::vector<BandConfig>& bands_;
    std::vector<TcpServer*>& servers_;

    std::atomic<bool>        running_{false};
    std::atomic<int>         current_band_{-1};
    int                      usb_errors_{0};   // consecutive UHD/USB failures

    std::vector<std::complex<float>> sample_buf_;
};
