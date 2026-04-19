# Scottish Bins

A [Home Assistant](https://www.home-assistant.io/) custom integration for Scottish council bin collection schedules.

## Supported Councils

Currently supported:

- **East Dunbartonshire** - full support for food caddy, green bin, and grey bin schedules

### Other Councils

Only East Dunbartonshire is supported right now. If you'd like support for your council, please [open an issue](https://github.com/d0ugal/scottish-bins-homeassistant/issues) with a link to your council's bin collection website. We'll investigate and add support where the data is accessible.

## Installation

### HACS (recommended)

1. Add this repository to HACS as a custom repository
2. Search for "Scottish Bins" and install
3. Restart Home Assistant

### Manual

Copy `custom_components/scottish_bins` into your Home Assistant `custom_components` directory and restart.

## Setup

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for "Scottish Bins"
3. Select your council
4. Search for your address by street, house name, or postcode
5. Select your property from the results

## Entities

Once configured, the integration creates:

- **Calendar** — shows upcoming bin collection events; works with the Home Assistant calendar card
- **Sensors** — one per bin type (e.g. Food caddy, Green bin, Grey bin), showing the date of the next collection with a `days_until` attribute
