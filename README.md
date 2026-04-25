# Alfa Lebanon — Home Assistant Integration

Pulls balance, data consumption, plan, and validity for an [Alfa](https://www.alfa.com.lb) (Lebanon) mobile line into Home Assistant.

Authenticates against the same mobile API used by the official Alfa Android app (phone number + password — no captcha, no cookies).

## Install via HACS (custom repository)

1. HACS → Integrations → ⋮ → **Custom repositories**
2. Repository: `https://github.com/moussa11/alfa-lb`, Category: **Integration**
3. Install **Alfa Lebanon**, restart Home Assistant
4. **Settings → Devices & Services → Add Integration → Alfa Lebanon**
5. Enter your 8-digit Alfa mobile number and account password

Multiple lines are supported — add the integration once per number.

## Manual install

Copy `custom_components/alfa_lb/` into your HA `config/custom_components/` and restart.

## Sensors

| Entity | Description |
| --- | --- |
| `sensor.alfa_<n>_balance` | Account balance (USD) |
| `sensor.alfa_<n>_data_used` | Data consumed in current cycle |
| `sensor.alfa_<n>_data_total` | Plan data quota |
| `sensor.alfa_<n>_data_remaining` | Data remaining |
| `sensor.alfa_<n>_plan` | Active plan name |
| `sensor.alfa_<n>_validity` | Plan expiry timestamp |
| `sensor.alfa_<n>_days_until_expiry` | Days until line expiry |
| `sensor.alfa_<n>_last_recharge_amount` | Last recharge amount (USD) |
| `sensor.alfa_<n>_last_recharge_date` | Last recharge timestamp |

The integration polls every 30 minutes.

## Disclaimer

Unofficial. Not affiliated with Alfa Telecom. Use at your own risk; credentials are stored by Home Assistant in its config entry store.
