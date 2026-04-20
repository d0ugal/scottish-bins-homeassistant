# UK Bins

A [Home Assistant](https://www.home-assistant.io/) custom integration for UK council bin collection schedules.

## Supported Councils

| Council | Status |
|---------|--------|
| Clackmannanshire | Supported |
| East Dunbartonshire | Supported |
| East Renfrewshire | Supported |
| Falkirk | Supported |
| North Ayrshire | Supported |
| South Ayrshire | Supported |
| West Lothian | Supported |

Don't see your council? [Open a request](https://github.com/d0ugal/uk-bins-homeassistant/issues/new) — upvoting existing requests (👍 on the first comment) helps prioritise which councils to add next.

## Installation

### HACS (recommended)

1. Add this repository to HACS as a custom repository
2. Search for "UK Bins" and install
3. Restart Home Assistant

### Manual

Copy `custom_components/uk_bins` into your Home Assistant `custom_components` directory and restart.

## Setup

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for "UK Bins"
3. Select your council
4. Search for your address by street, house name, or postcode
5. Select your property from the results

## Entities

Once configured, the integration creates:

- **Calendar** — shows upcoming bin collection events; works with the Home Assistant calendar card
- **Sensors** — one per bin type (e.g. Food caddy, Green bin, Grey bin), showing the date of the next collection with a `days_until` attribute
