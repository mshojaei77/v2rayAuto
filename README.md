# V2Ray Auto Configuration Updater

This script is designed to automatically update V2Ray configuration files from various subscription links and push the changes to a GitHub repository.

### ✅ Tested Configs : 

<img src="https://github.com/mshojaei77/v2rayAuto/assets/76538971/ce8d713e-0baf-44a0-94cd-2cfa0c4e0001" width="100" height="100"> [Mix](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/mix)

<img src="https://github.com/mshojaei77/v2rayAuto/assets/76538971/6626abb1-2280-4273-89e0-51086c5f07dd" width="50" height="50">  [HamrahAval](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/auto)

<img src="https://github.com/mshojaei77/v2rayAuto/assets/76538971/043634fd-dd50-44ec-9742-656d02e38b96" width="80" height="50">  [Irancell](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/mtn)








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

## Location-specific :

| Country Codes | Subscription Link                                            |  Notes                                                                                                 |
|-----------------------------|-----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| `US`, `GB`, `CA`, `AU`, `IE`, `NZ`  | [English Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/English) | This link provides a subscription to servers located in the United States, the United Kingdom, Canada, Australia, Ireland, and New Zealand. It is suitable for users that want to use servers in these areas for specific reasons, such as faster connection speeds or better streaming quality. |
| `DE`, `FR`, `NL`, `FI`, `IT`, `AL`, `TR`, `SE`   | [Europe Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/Europe) | This link provides a subscription to servers located in Germany, France, the Netherlands, Finland, Italy, Albania, Turkey, and Sweden. It is ideal for users that want to access content from these regions. |
| `IR`    | [IRAN Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/IRAN) | This link provides a subscription to servers located in Iran. It is tailored for users who are in Iran or those who want to access content from Iran. |

## Security-specific :

| Security                    | Subscription Link                                            | Notes                                                                                                 |
|-----------------------------|-----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| Reality                       | [Reality Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/reality) | This link provides a subscription to servers that prioritize security and privacy, with a focus on real-world privacy measures. It is suitable for users who are particularly concerned about their online anonymity and privacy.  |
| TLS          | [TLS Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/tls) |  This link provides a subscription to servers that use TLS (Transport Layer Security) for secure communication. It is ideal for users who want to ensure that their data is encrypted during transmission. |

## Type-specific :

| Security                    | Subscription Link                                            | Notes                                                                                                 |
|-----------------------------|-----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| WebSocket                    | [WebSocket Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/ws) |  This link provides a subscription to servers that use the WebSocket protocol, which is often used for bypassing web filtering and censorship. It is suitable for users who require WebSocket support. |
| TCP          | [TCP Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/tcp) | This link provides a subscription to servers that use the TCP protocol, which is a reliable and commonly used protocol for internet communication. It is ideal for users who prefer the stability of TCP connections.  |
| gRPC          | [gRPC Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/grpc) | This link provides a subscription to servers that use the gRPC protocol, which is a high-performance, open-source framework for remote procedure calls (RPCs). It is suitable for users who need to use gRPC for their applications. |

## Ping-specific :

| Security                    | Subscription Link                                            | Notes                                                                                                 |
|-----------------------------|-----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| High Ping                       | [High Ping Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/Highping) | This link provides a subscription to servers with higher ping times, which might be necessary for users with slower internet connections or those who prioritize reliability over speed.  |
| Medium Ping          | [Medium Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/Midping) | This link provides a subscription to servers with medium ping times, offering a balance between speed and reliability. It is ideal for users with moderate internet speeds.  |


## Oprator-specific (on  Worker)
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

