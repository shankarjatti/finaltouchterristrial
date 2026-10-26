#pragma once
#include <uhd/usrp/multi_usrp.hpp>
#include <uhd/types/tune_request.hpp>
#include <complex>
#include <vector>
#include <string>

// ─────────────────────────────────────────────────────────────────────────────
//  Band descriptor
// ─────────────────────────────────────────────────────────────────────────────
struct BandConfig {
    std::string name;       // e.g. "DMR446"
    double      freq_hz;    // centre frequency
    int         tcp_port;   // TCP server port for this band
    double      dwell_sec;  // active streaming time for this band, per cycle
};

// ─────────────────────────────────────────────────────────────────────────────
//  USRP Controller
//  - Opens USRP B210
//  - Configures: samp_rate = 1 MHz, decimation 5:1 → 200 kSps
//  - Provides tune() and stream() primitives
// ─────────────────────────────────────────────────────────────────────────────
class UsrpController {
public:
    // B210 hardware sample rate — set directly to 200 kSps.
    // UHD + AD9361 DSP chain handles decimation internally with proper
    // anti-alias filtering. No software decimation needed.
    static constexpr double OUT_SAMPLE_RATE = 200'000.0;  // 200 kSps to TCP
    static constexpr double DEFAULT_GAIN    = 40.0;        // dB — used only if
                                                            // SECURECOM_RX_GAIN_DB is unset

    explicit UsrpController(const std::string& device_args = "");
    ~UsrpController();

    // Set centre frequency, wait for LO lock
    bool tune(double freq_hz);

    // Stream `num_samples` complex<float> samples into `buf`
    // Returns actual samples received (-1 on error)
    int  stream(std::vector<std::complex<float>>& buf, size_t num_samples);

    // Start / stop the RX streamer
    void start_stream();
    void stop_stream();

    double get_actual_freq()  const;
    double get_actual_gain()  const;
    bool   is_locked()        const;

    uhd::usrp::multi_usrp::sptr usrp;

private:
    uhd::rx_streamer::sptr  rx_stream_;
    uhd::stream_args_t      stream_args_;
    bool                    streaming_{false};
};
