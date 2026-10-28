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
    // Silent gap AFTER this band's dwell. Per-band rather than one shared
    // constant: with 8 bands in the cycle the gap is no longer a rounding
    // error, it is a real share of wall-clock time. Only needs to be long
    // enough to push zero-fill keep-alive to the TCP clients.
    double      gap_sec;
    // RX sample rate for THIS band's dwell slot. Every terrestrial band uses
    // UsrpController::OUT_SAMPLE_RATE (200 kSps) -- ADS-B is the exception:
    // 1090ES Mode-S needs real instantaneous bandwidth no amount of
    // downstream resampling can manufacture, so its dwell slot requests a
    // genuinely wider hardware rate (see UsrpController::set_rate).
    double      samp_rate_hz;
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

    // Change RX sample rate for the upcoming dwell. Called every dwell cycle
    // alongside tune() -- the RX stream is already torn down and rebuilt on
    // every cycle regardless of band (see BurstController::do_dwell), so
    // this rides the same rebuild rather than adding a new one. Logs
    // requested vs. actual (UHD may not hit the exact value asked for) the
    // same way tune() logs target vs. actual frequency.
    void set_rate(double samp_rate_hz);

    double get_current_rate() const { return current_rate_; }

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
    double                  current_rate_{OUT_SAMPLE_RATE};
};
