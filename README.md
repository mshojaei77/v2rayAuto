# V2Ray Auto Configuration Updater

This script is designed to automatically update V2Ray configuration files from various subscription links and push the changes to a GitHub repository.


### ✅ Automatic Tested Configs : [Subscription Link ](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/auto) | [Subscription Link on Worker](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/original=yes) 

## Protocol-specific :

| Protocol                    | Subscription Link                                            | Notes                                                                                                 |
|-----------------------------|-----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| VMess                       | [VMess Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/vmess) | VMess is a versatile protocol with strong encryption. Refer to VMess documentation for setup details. |
| Shadowsocks (SS)            | [Shadowsocks Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/ss) | Shadowsocks offers a secure and fast proxy. Check Shadowsocks documentation for proper configuration. |
| VLESS                       | [VLESS Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/vless) | VLESS is a more secure version of VMess. Follow VLESS documentation for a detailed setup guide.       |
| Trojan                      | [Trojan Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/trojan) | Trojan provides a secure and efficient tunnel. Consult Trojan documentation for configuration tips.   |
| TUIC                        | [TUIC Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/tuic) | TUIC is designed for low-latency communication. Refer to TUIC documentation for optimal usage.       |
| Hysteria                    | [Hysteria Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/hysteria) | Hysteria provides a WebSocket proxy for V2Ray, a popular open-source VPN protocol. It is built on the QUIC protocol and masquerades as an HTTP/3 server, making it difficult to detect and block.  |
| HY2                         | [Hysteria2 Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/hy2) | HY2 is a hybrid protocol with features of both VLESS and Trojan.  |
| SOCKS5                       | [SOCKS5 Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/socks5) |  SOCKS5 offer faster speeds than traditional VPNs and are ideal for activities such as video streaming, live calls, and traffic-intensive data gathering.    |
| ShadowsocksR (SSR)          | [SSR Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/ssr) | SSR was developed based on the original Shadowsocks project, adding various encryption protocols and additional features. |
| Warp          | [Warp Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/warp) | Warp is a mobile-only VPN service developed by Cloudflare, designed to enhance Internet performance and security. Unlike traditional VPNs, Warp does not mask your IP address, but it does encrypt all traffic from your device to the edge of Cloudflare's network, which helps protect against unencrypted connections and improves performance. Warp uses the WireGuard protocol, which is more efficient than legacy VPN protocols, and it is built around the WireGuard variant called BoringTun |
| WireGuard         | [WireGuard Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/wireguard) | WireGuard is a modern, open-source VPN protocol that uses public-key cryptography to create an encrypted tunnel between devices. |

⚠  **Some Subscription links may contain large amounts of Configurations, and may cause errors and overload.**

## Security-specific :

| Security                    | Subscription Link                                            | Notes                                                                                                 |
|-----------------------------|-----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| Reality                       | [Reality Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/reality) | VMess is a versatile protocol with strong encryption. Refer to VMess documentation for setup details. |
| TLS          | [TLS Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/tls) | Shadowsocks offers a secure and fast proxy. Check Shadowsocks documentation for proper configuration. |

## Location-specific :

| Country Codes | Subscription Link                                            |
|----------|-----------------------------------------------------------------|
| `US`, `GB`, `CA`, `AU`, `IE`, `NZ`  | [English Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/English) |
| `DE`, `FR`, `NL`, `FI`, `IT`, `AL`, `TR`, `SE`   | [Europe Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/Europe) |
| `IR`    | [IRAN Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/IRAN) |

## Oprator-specific
sub link | oprator      
---         | --- 
[all](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub) | همه
[mci](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/mci)         | همراه اول    
[mtn](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/mtn)         | ایرانسل      
[ztl](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/ztl)         | زیتل
[afn](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/afn)         | افرانت       
[ast](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/ast)         | آسیاتک       
[dbn](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/dbn)         | دیده‌بان     
[dtk](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/dtk)         | داتک    
[fnv](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/fnv)         | فن‌آوا        
[hwb](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/hwb)         | های‌وب        
[mbt](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/mbt)         | مبین‌نت       
[mkh](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/mkh)         | مخابرات      
[prs](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/prs)         | پارس‌آنلاین    
[psm](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/psm)         | پیشگامان    
[rsp](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/rsp)         | رسپینا       
[rtl](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/rtl)         | رایتل        
[sht](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/sht)         | شاتل         
[apt](https://only-vless.fcrcvsgmwmspdgwpkl.workers.dev/sub/apt)         | عصر تلکام    

---         | ---

thanks vfarid for [worker projects](https://github.com/vfarid/v2ray-worker-sub)

## GUI Clients
- Windows
  - [HiddifyNext](https://github.com/hiddify/hiddify-next)
  - [NekoRay](https://github.com/Matsuridayo/nekoray)
  - [v2rayN](https://github.com/2dust/v2rayN)

- Android
  - [HiddifyNext](https://github.com/hiddify/hiddify-next)
  -  [v2rayNG](https://github.com/2dust/v2rayNG)

- iOS & macOS arm64
  - [Mango](https://github.com/arror/Mango)
  - [FoXray](https://apps.apple.com/app/foxray/id6448898396)
- macOS arm64 & x64
  - [V2rayU](https://github.com/yanue/V2rayU)
  - [FoXray](https://apps.apple.com/app/foxray/id6448898396)
- Linux
  - [v2rayA](https://github.com/v2rayA/v2rayA)
  - [NekoRay](https://github.com/Matsuridayo/nekoray)

