#pragma once
#include "usrp_controller.h"
#include "tcp_server.h"
#include <vector>
#include <atomic>
#include <memory>

// ─────────────────────────────────────────────────────────────────────────────
//  BurstController
//
//  Cycles through the configured bands in sequence, e.g.:
//    DMR446  → [dwell BandConfig::dwell_sec] → [gap GAP_SEC]
//    NXDN96  → [dwell BandConfig::dwell_sec] → [gap GAP_SEC]
//    P25     → [dwell BandConfig::dwell_sec] → [gap GAP_SEC]
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
    static constexpr double GAP_SEC   = 1.0;   // silent gap between bands

    // samples_per_chunk: how many decimated samples per TCP write burst
    static constexpr size_t SAMPLES_PER_CHUNK = 2000;  // 200kSps / 100 = 10ms chunks

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
