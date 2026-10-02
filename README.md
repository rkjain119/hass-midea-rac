<p align="center">
  <img src="https://raw.githubusercontent.com/rkjain119/hass-midea-rac/main/custom_components/midea_rac/brand/logo.png" alt="Midea" width="320">
</p>

# Midea RAC Wi-Fi for Home Assistant

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rkjain119&repository=hass-midea-rac&category=integration)
[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=midea_rac)

Control Midea air conditioners that use the **Midea RAC Wi-Fi V2** app
(`com.midea.mideasmartac`, sold in India) from Home Assistant.

These ACs don't use Midea's usual cloud, so existing Midea integrations such as
`midea_ac_lan` and `msmart-ng` can't find them. The app is built on the **Jio Smart Living**
(OBLO) IoT platform. This integration uses the same cloud MQTT connection the app uses, so you
get full control and sensors in Home Assistant.

> **Unofficial community project.** Not affiliated with or endorsed by Midea or Jio. The Midea
> name and logo belong to their owners. Control goes through the cloud and needs internet. It
> could stop working if the vendor changes the API.

## Features

Each air conditioner gets:

- **Climate entity**: power, target temperature (17–30 °C), mode (cool / auto / dry /
  fan only), fan speed (Low / Medium / High / Auto), presets (**Eco**, **Sleep**,
  **Boost** = turbo), vertical swing (on = swing, off = fixed at the top) and horizontal
  swing (on / off).
- **Fan**: the fan speed as its own entity, so dashboards can show a speed control (with an
  Auto preset).
- **Gear**: Midea's FC1–FC6 capacity levels, which limit compressor power to save energy.
  FC6 is turbo. The AC only accepts a gear in **cool** mode.
- **Switches**: Power (resumes the last mode), Display, Self-clean, and Anti-mildew (dries the coil after the AC is
  switched off).
- **Sensors**: indoor (room) temperature, outdoor temperature, energy used (kWh), power (W),
  and Wi-Fi signal (dBm) and link quality as diagnostic sensors.

All ACs on the account are found automatically.

## Requirements

- Home Assistant 2024.12 or newer. Version 2026.3 or newer is needed to show the Midea logo in
  the UI.
- At least one AC set up and working in the **Midea RAC Wi-Fi V2** app.
- The phone number you log in to the app with. A one-time OTP is sent to it by SMS.

## Installation

### HACS (recommended)

1. Click the **Open in HACS** button above. Or, in HACS, open the ⋮ menu →
   **Custom repositories** and add `https://github.com/rkjain119/hass-midea-rac` with type
   **Integration**.
2. Search for **Midea RAC Wi-Fi** and click **Download**.
3. Restart Home Assistant.

### Manual

Copy `custom_components/midea_rac` into your Home Assistant `config/custom_components/`
folder and restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration** and choose **Midea RAC Wi-Fi**
   (or click the **Add integration** button above).
2. Enter the phone number you use in the Midea RAC Wi-Fi V2 app, for example
   `+9199XXXXXXXX`. A 10-digit number is assumed to be Indian (`+91`).
3. Enter the OTP you receive by SMS.

Your ACs appear as devices with a climate entity and the sensors above. The session is saved
and the connection comes back on its own after restarts or network drops. If the session ever
expires, Home Assistant shows a **re-authenticate** prompt that sends a new OTP.

## Where to find the data

- **AC controls and room temperature:** the climate card. Its "Current temperature" is the
  indoor reading.
- **Indoor/outdoor temperature, energy and power:** separate sensors on the AC's device page
  and the area dashboard. The climate card has no field for outdoor temperature.
- **Wi-Fi signal and link quality:** diagnostic sensors. Home Assistant hides these from
  auto-generated dashboards, so look under **Diagnostic** on the device page
  (**Settings → Devices & services → Midea RAC Wi-Fi →** your AC).
- **Energy dashboard:** add the AC's *Energy* sensor under **Settings → Dashboards → Energy →
  Individual devices**.

## Supported devices

ACs controlled by the **Midea RAC Wi-Fi V2** app, for example Midea India split ACs with the
`MIMM310B58` Wi-Fi module. If your AC works in that app, it should work here.

Tested with Home Assistant 2026.9 and two Midea split ACs on one account.

## How it works

- **Login:** the phone number and OTP go to the same cloud login the app uses, which returns
  a session token.
- **Connection:** the integration keeps one TLS MQTT connection to the cloud broker. It
  receives device state and polls every 30 seconds.
- **Control:** settings are changed with the same commands the app sends.

You don't need root, hardware changes, or local network access to the AC.

## Troubleshooting

Turn on debug logging and include the logs when you open an issue:

```yaml
logger:
  logs:
    custom_components.midea_rac: debug
```

## Limitations

- Needs internet and the vendor's cloud to be online.
- Could break if the vendor changes the API or login.
- Features that only work over the app's Bluetooth or local connection aren't available.

## License

MIT. See [LICENSE](LICENSE).
