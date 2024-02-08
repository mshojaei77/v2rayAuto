# V2Ray Auto Configuration Updater

This script is designed to automatically update V2Ray configuration files from various subscription links and push the changes to a GitHub repository.

## Location-specific Configurations:

| Language | Subscription Link                                            |
|----------|-----------------------------------------------------------------|
| English Countries | [English Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/English) |
| Europe   | [Europe Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/Europe) |
| IRAN     | [IRAN Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/IRAN) |
|✅ MIX  | [MIX Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/auto) |

## Protocol-specific Configurations:

| Protocol                    | Subscription Link                                            | Notes                                                                                                 |
|-----------------------------|-----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| VMess                       | [VMess Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/vmess) | VMess is a versatile protocol with strong encryption. Refer to VMess documentation for setup details. |
| Shadowsocks (SS)            | [Shadowsocks Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/ss) | Shadowsocks offers a secure and fast proxy. Check Shadowsocks documentation for proper configuration. |
| VLESS                       | [VLESS Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/vless) | VLESS is a more secure version of VMess. Follow VLESS documentation for a detailed setup guide.       |
| Trojan                      | [Trojan Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/trojan) | Trojan provides a secure and efficient tunnel. Consult Trojan documentation for configuration tips.   |
| TUIC                        | [TUIC Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/tuic) | TUIC is designed for low-latency communication. Refer to TUIC documentation for optimal usage.       |
| Hysteria                    | [Hysteria Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/hysteria) | Hysteria is suitable for scenarios with high packet loss. Check Hysteria documentation for guidance.  |
| HY2                         | [HY2 Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/hy2) | HY2 is a hybrid protocol with features of both VLESS and Trojan. See HY2 documentation for setup details. |
| SOCKS5                       | [SOCKS5 Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/socks5) | SOCKS5 is a widely used proxy protocol. Review SOCKS5 documentation for proper implementation.        |
| ShadowsocksR (SSR)          | [SSR Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/ssr) | SSR is an enhanced version of Shadowsocks. Refer to SSR documentation for detailed setup instructions. |

⚠  **Some Subscription links may contain large amounts of Configurations, and may cause errors and overload.**

## GUI Clients
- Windows
  - [v2rayN](https://github.com/2dust/v2rayN)
  - [HiddifyNext](https://github.com/hiddify/hiddify-next)
  - [NekoRay](https://github.com/Matsuridayo/nekoray)

- Android
  - [v2rayNG](https://github.com/2dust/v2rayNG)
  - [HiddifyNext](https://github.com/hiddify/hiddify-next)
- iOS & macOS arm64
  - [Mango](https://github.com/arror/Mango)
  - [FoXray](https://apps.apple.com/app/foxray/id6448898396)
- macOS arm64 & x64
  - [V2rayU](https://github.com/yanue/V2rayU)
  - [FoXray](https://apps.apple.com/app/foxray/id6448898396)
- Linux
  - [v2rayA](https://github.com/v2rayA/v2rayA)
  - [NekoRay](https://github.com/Matsuridayo/nekoray)


## On worker
#### main project: https://github.com/vfarid/v2ray-worker-sub

لینک ساب کامل روی ورکر: 
https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub
همراه اول:
https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/mci
ایرانسل:
https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/mtn

و یا همین لینک را همراه آی‌پی تمیز در اپ خود اضافه کنید:

https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/1.2.3.4
می‌توانید دامین آی‌پی تمیز نیز استفاده کنید:

https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/mci.ircf.space
می‌توانید با متغیر max تعداد کانفیگ را مشخص کنید:

https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/1.2.3.4?max=200

همچنین می‌توانید با متغیر original با عدد 0 یا 1 و یا با yes/no مشخص کنید که کانفیگ‌های اصلی (ترکیب نشده با ورکر) هم در خروجی آورده شوند یا نه:

https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/1.2.3.4?max=200&original=yes

https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/1.2.3.4?max=200&original=0
