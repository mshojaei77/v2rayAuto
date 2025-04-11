# V2Ray Auto Configuration Updater

This script is designed to automatically update V2Ray configuration files from various subscription links and push the changes to a GitHub repository.

### Tested Configs : 
## [Auto Tested](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/subs/auto) <img src="https://github.com/mshojaei77/v2rayAuto/assets/76538971/ce8d713e-0baf-44a0-94cd-2cfa0c4e0001" width="30" height="30"> 

# Protocol-specific :

| Protocol                    | Subscription Link                                            | Notes                                                                                                 |
|-----------------------------|-----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| VMess                       | [VMess Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/subs/vmess) | VMess is a versatile protocol with strong encryption. Refer to VMess documentation for setup details. |
| Shadowsocks (SS)            | [Shadowsocks Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/subs/ss) | Shadowsocks offers a secure and fast proxy. Check Shadowsocks documentation for proper configuration. |
| VLESS                       | [VLESS Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/subs/vless) | VLESS is a more secure version of VMess. Follow VLESS documentation for a detailed setup guide.       |
| Trojan                      | [Trojan Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/subs/trojan) | Trojan provides a secure and efficient tunnel. Consult Trojan documentation for configuration tips.   |
| TUIC                        | [TUIC Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/subs/tuic) | TUIC is designed for low-latency communication. Refer to TUIC documentation for optimal usage.       |
| Hysteria                    | [Hysteria Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/subs/hysteria) | Hysteria provides a WebSocket proxy for V2Ray, a popular open-source VPN protocol. It is built on the QUIC protocol and masquerades as an HTTP/3 server, making it difficult to detect and block.  |
| HY2                         | [Hysteria2 Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/subs/hy2) | HY2 is a hybrid protocol with features of both VLESS and Trojan.  |
| SOCKS5                       | [SOCKS5 Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/subs/socks5) |  SOCKS5 offer faster speeds than traditional VPNs and are ideal for activities such as video streaming, live calls, and traffic-intensive data gathering.    |
| ShadowsocksR (SSR)          | [SSR Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/subs/ssr) | SSR was developed based on the original Shadowsocks project, adding various encryption protocols and additional features. |
| Warp          | [Warp Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/subs/warp) | Warp is a mobile-only VPN service developed by Cloudflare, designed to enhance Internet performance and security. Unlike traditional VPNs, Warp does not mask your IP address, but it does encrypt all traffic from your device to the edge of Cloudflare's network, which helps protect against unencrypted connections and improves performance. Warp uses the WireGuard protocol, which is more efficient than legacy VPN protocols, and it is built around the WireGuard variant called BoringTun |
| WireGuard         | [WireGuard Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/subs/wireguard) | WireGuard is a modern, open-source VPN protocol that uses public-key cryptography to create an encrypted tunnel between devices. |

⚠  **Some Subscription links may contain large amounts of Configurations, and may cause errors and overload.**


## Clients
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

## Security-specific :

| Security                    | Subscription Link                                            | Notes                                                                                                 |
|-----------------------------|-----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| Reality                       | [Reality Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/subs/reality) | This link provides a subscription to servers that prioritize security and privacy, with a focus on real-world privacy measures. It is suitable for users who are particularly concerned about their online anonymity and privacy.  |
| TLS          | [TLS Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/subs/tls) |  This link provides a subscription to servers that use TLS (Transport Layer Security) for secure communication. It is ideal for users who want to ensure that their data is encrypted during transmission. |

## Type-specific :

| Security                    | Subscription Link                                            | Notes                                                                                                 |
|-----------------------------|-----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| WebSocket                    | [WebSocket Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/subs/ws) |  This link provides a subscription to servers that use the WebSocket protocol, which is often used for bypassing web filtering and censorship. It is suitable for users who require WebSocket support. |
| TCP          | [TCP Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/subs/tcp) | This link provides a subscription to servers that use the TCP protocol, which is a reliable and commonly used protocol for internet communication. It is ideal for users who prefer the stability of TCP connections.  |
| gRPC          | [gRPC Configuration](https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/subs/grpc) | This link provides a subscription to servers that use the gRPC protocol, which is a high-performance, open-source framework for remote procedure calls (RPCs). It is suitable for users who need to use gRPC for their applications. |



