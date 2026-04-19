"""Constants for the Scottish Bins integration."""

DOMAIN = "scottish_bins"

CONF_COUNCIL = "council"
CONF_UPRN = "uprn"
CONF_ADDRESS = "address"

COUNCIL_EAST_DUNBARTONSHIRE = "east_dunbartonshire"

COUNCILS = {
    COUNCIL_EAST_DUNBARTONSHIRE: "East Dunbartonshire",
}

# CSS class → display name for each council's bin types
COUNCIL_BINS: dict[str, dict[str, str]] = {
    COUNCIL_EAST_DUNBARTONSHIRE: {
        "food-caddy": "Food caddy",
        "garden-bin": "Green bin",
        "rubbish-bin": "Grey bin",
    },
}
