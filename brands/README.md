# Home Assistant brand assets

These four PNGs are the icon/logo for the `alfa_lb` custom integration in the
size and shape required by [home-assistant/brands](https://github.com/home-assistant/brands).

| File | Size | Purpose |
| --- | --- | --- |
| `custom_integrations/alfa_lb/icon.png` | 256x256 | Standard-DPI icon shown in Settings -> Devices & services |
| `custom_integrations/alfa_lb/icon@2x.png` | 512x512 | Retina version of the same icon |
| `custom_integrations/alfa_lb/logo.png` | 256x256 | Standard-DPI logo |
| `custom_integrations/alfa_lb/logo@2x.png` | 512x512 | Retina version of the logo |

Source: `ic_splash_logo.png` from the official Alfa Lebanon Android app
(`com.apps2you.alfa` v5.2.86), resized via `sips`.

## Submitting to home-assistant/brands

To make the icon render in Home Assistant's device cards for everyone:

```bash
git clone https://github.com/home-assistant/brands.git
cd brands
mkdir -p custom_integrations/alfa_lb
cp /path/to/alfa-lb/brands/custom_integrations/alfa_lb/*.png custom_integrations/alfa_lb/
git checkout -b alfa_lb-brand
git add custom_integrations/alfa_lb
git commit -m "Add custom_integrations/alfa_lb"
git push origin alfa_lb-brand
gh pr create --fill
```

Until the PR is merged, HA will fall back to the default placeholder; the
integration still works, just without the Alfa logo on the device card.
