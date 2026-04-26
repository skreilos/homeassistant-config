# Home Assistant Consistency Audit

- Entities in snapshot: **2160**
- Missing references in active config: **21**
- Legacy entity IDs remaining: **36**
- Stale customize keys: **0**

## Priority Findings
- Fix missing entity references in active files (`automations.yaml`, `scenes.yaml`, `customize.yaml`).
- Consider consolidating duplicate area names (`Zimmer Julian`) into one canonical area.
- Run export scripts after each device/rename change and commit snapshots.

## Missing References (Active Config)
- `switch.sz_joshua_aquarium` in `automations.yaml`
- `switch.sz_julian_aquarium` in `automations.yaml`
- `media_player.android_tv_10_0_0_22` in `automations.yaml`
- `sensor.ms_kuche` in `automations.yaml`
- `light.aquarium_joshua` in `automations.yaml`
- `light.aquarium_julian` in `automations.yaml`
- `scene.wohnraum_dimm_high` in `automations.yaml`
- `scene.wohnraum` in `automations.yaml`
- `scene.wohnraum_off` in `automations.yaml`
- `scene.buro_on` in `automations.yaml`
- `scene.buro_off` in `automations.yaml`
- `scene.esstisch_high` in `automations.yaml`
- `scene.esstisch_off_motion_off` in `automations.yaml`
- `scene.esstisch_high_duplicate` in `automations.yaml`
- `sensor.web_scrape_2` in `automations.yaml`
- `sensor.website_seebadiwollishofen` in `automations.yaml`
- `sensor.website_badiletzigraben` in `automations.yaml`
- `sensor.website_coiffeurnora` in `automations.yaml`
- `sensor.website_massagepraxis` in `automations.yaml`
- `sensor.website_spatzenaescht` in `automations.yaml`
- `switch.schalter_zimmer_julian_schreibtisch` in `scenes.yaml`

## Stale Customize Keys
- none

## Legacy Entity IDs (Remaining)
- `button.button_spielzimmer_identify_6`
- `button.button_werktisch_identify_6`
- `button.deckenlicht_kinderspielzimmer_identify`
- `button.spielzimmer_deckenlicht_identify`
- `button.werktisch_licht_identify_2`
- `input_number.eg_sound_spielzimmer`
- `media_player.kinderschlafzimmer`
- `media_player.spielzimmer`
- `number.deckenlicht_kinderspielzimmer_on_level`
- `number.deckenlicht_kinderspielzimmer_on_off_transition_time`
- `number.deckenlicht_kinderspielzimmer_start_up_color_temperature`
- `number.deckenlicht_kinderspielzimmer_start_up_current_level`
- `number.kinderschlafzimmer_balance`
- `number.kinderschlafzimmer_bass`
- `number.kinderschlafzimmer_treble`
- `number.spielzimmer_balance`
- `number.spielzimmer_bass`
- `number.spielzimmer_deckenlicht_start_up_current_level`
- `number.spielzimmer_treble`
- `number.werktisch_licht_on_level_2`
- `number.werktisch_licht_on_off_transition_time_2`
- `number.werktisch_licht_start_up_current_level_2`
- `select.deckenlicht_kinderspielzimmer_start_up_behavior`
- `select.spielzimmer_deckenlicht_start_up_behavior`
- `select.werktisch_licht_start_up_behavior_2`
- `sensor.button_kinderzimmer_lqi_4`
- `sensor.button_kinderzimmer_rssi_4`
- `sensor.button_spielzimmer_battery_6`
- `sensor.button_werktisch_battery_6`
- `sensor.button_werktisch_lqi_7`
- `sensor.button_werktisch_rssi_7`
- `update.button_spielzimmer_firmware`
- `update.button_werktisch_firmware`
- `update.deckenlicht_kinderspielzimmer_firmware`
- `update.spielzimmer_deckenlicht_firmware`
- `update.werktisch_licht_firmware`

## Areas
- `Aquarien`
- `Bad`
- `Bad (Stay On)`
- `Büro`
- `Esstisch`
- `Gang`
- `Kinderschlafzimmer`
- `Küche`
- `Sofa`
- `Sonos Roam`
- `TV`
- `Trolley`
- `WC`
- `Wohnzimmer`
- `Zimmer Joshua`
- `Zimmer Julian`
- `Zimmer Julian`
- `Zimmer Stephan`
