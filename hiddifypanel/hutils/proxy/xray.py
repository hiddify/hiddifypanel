import datetime
import json
from flask import request, g
from hiddifypanel import hutils
from hiddifypanel.models import ProxyTransport, ProxyL3, ProxyProto, Domain, User, ConfigEnum, hconfig
from flask_babel import gettext as _
from urllib.parse import urlencode,quote
OUTBOUND_LEVEL = 8


def is_muxable_agent(proxy: dict) -> bool:
    if not proxy.get('mux_enable'):
        return False
    if proxy.get('mux_enable') == "xray" and g.user_agent.get('is_singbox'):
        return False
    if proxy.get('mux_enable') == "singbox" and not g.user_agent.get('is_singbox'):
        return False
    return True


def to_link(proxy: dict) -> str | dict:
    if 'error' in proxy:
        return proxy

    orig_name_link = (proxy['extra_info'] + " " + proxy["name"]).strip()
    name_link = hutils.encode.url_encode(orig_name_link)
    if proxy['proto'] == 'vmess':
        # print(proxy)
        vmess_type = None
        if proxy["transport"] == 'tcp':
            vmess_type = 'http'
        if 'grpc_mode' in proxy:
            vmess_type = proxy['grpc_mode']
        vmess_data = {"v": "2",
                      "ps": orig_name_link,
                      "add": proxy['server'],
                      "port": proxy['port'],
                      "id": proxy["uuid"],
                      "aid": 0,
                      "scy": proxy['cipher'],
                      "net": proxy["transport"],
                      "type": vmess_type or "none",
                      "host": proxy.get("host", ""),
                      "alpn": proxy.get("alpn", "h2,http/1.1"),
                      "path": proxy["path"] if "path" in proxy else "",
                      "tls": "tls" if "tls" in proxy["l3"] or "quic" in proxy['l3'] else "",
                      "sni": proxy["sni"],
                      "fp": proxy["fingerprint"]
                      }
        
        if 'reality' in proxy["l3"]:
            vmess_data['tls'] = "reality"
            vmess_data['pbk'] = proxy['reality_pbk']
            vmess_data['sid'] = proxy['reality_short_id']
        if proxy.get('transport') in {ProxyTransport.xhttp}:
            vmess_data['core']='xray'
            _add_xhttp_extra(vmess_data,proxy)
        add_tls_tricks_to_dict(vmess_data, proxy)
        add_mux_to_dict(vmess_data, proxy)

        return "vmess://" + hutils.encode.do_base_64(f'{json.dumps(vmess_data,cls=hutils.proxy.ProxyJsonEncoder)}')
    if proxy['proto'] == 'ssh':
        # baseurl = 'ssh://'
        # if g.user_agent.get('is_streisand'):
        #     streisand_ssh = hutils.encode.do_base_64(f'{proxy["uuid"]}:0:{proxy["private_key"]}::@{proxy["server"]}:{proxy["port"]}')
        #     baseurl += f'{streisand_ssh}#{name_link}'
        # else:
        hk = ",".join(proxy["host_keys"])
        pk = proxy["private_key"].replace('\n', '')
        q={
            'file':'ssh',
            'hk':hk,
            'pk':pk,
            'private_key':pk,
            'authentication':0,
            'passphrase':'',                
        }
        return f"ssh://{proxy["uuid"]}@{proxy["server"]}:{proxy["port"]}/?{urlencode(q,quote_via=quote)}#{name_link}"
            # baseurl += f'{proxy["uuid"]}@{proxy["server"]}:{proxy["port"]}/?file=ssh&pk={pk}&hk={hk}&private_key={pk}&authentication=0&passphrase#{name_link}'

        # return baseurl
    if proxy['proto'] == "ssr":
        baseurl = f'ssr://{proxy["cipher"]}:{proxy["uuid"]}@{proxy["server"]}:{proxy["port"]}'
        return baseurl
    if proxy['proto'] in ['ss', 'v2ray']:
        baseurl = f'ss://{hutils.encode.do_base_64(proxy["cipher"] + ":" + proxy["password"])}@{proxy["server"]}:{proxy["port"]}'

        if proxy['transport'] == 'shadowsocks':
            return f'{baseurl}#{name_link}'
        if proxy['transport'] == 'faketls':
            return f'{baseurl}?plugin=obfs-local&obfs-host={proxy["fakedomain"]}&obfs=http&udp-over-tcp=true#{name_link}'
        if proxy['transport'] == 'shadowtls':
            return "ShadowTLS is Not Supported for this platform"
            # return f'{baseurl}?plugin=v2ray-plugin&path={proxy["proxy_path"]}&host={proxy["fakedomain"]}&udp-over-tcp=true#{name_link}'
        if proxy['proto'] == 'v2ray':
            return f'{baseurl}?plugin=v2ray-plugin&mode=websocket&path={proxy["proxy_path"]}&host={proxy["sni"]}&tls&udp-over-tcp=true#{name_link}'

    if proxy['proto'] == 'tuic':
        baseurl = f'tuic://{proxy["uuid"]}:{proxy["uuid"]}@{proxy["server"]}:{proxy["port"]}?congestion_control=cubic&udp_relay_mode=native&sni={proxy["sni"]}&alpn=h3'
        if proxy['mode'] == 'Fake' or proxy['allow_insecure']:
            baseurl += "&allow_insecure=1"
        return f"{baseurl}#{name_link}"
    if proxy['proto'] == 'hysteria2':
        baseurl = f'hysteria2://{proxy["uuid"]}@{proxy["server"]}:{proxy["port"]}?hiddify=1&obfs=salamander&obfs-password={proxy["hysteria_obfs_password"]}&sni={proxy["sni"]}'
        if proxy['mode'] == 'Fake' or proxy['allow_insecure']:
            baseurl += "&insecure=1&allow_insecure=1"
        return f"{baseurl}#{name_link}"
    if proxy['proto'] == ProxyProto.wireguard:
        if g.user_agent.get('is_streisand'):
            return f'wireguard://{proxy["server"]}:{proxy["port"]}?private_key={proxy["wg_pk"]}&peer_public_key={proxy["wg_server_pub"]}&pre_shared_key={proxy["wg_psk"]}&reserved=0,0,0#{name_link}'
        else:
            # hiddify_format =
            # f'wg://{proxy["server"]}:{proxy["port"]}/?pk={proxy["wg_pk"]}&local_address={proxy["wg_ipv4"]}/32&peer_pk={proxy["wg_server_pub"]}&pre_shared_key={proxy["wg_psk"]}&workers=4&mtu=1380&reserved=0,0,0&ifp={proxy["wg_noise_trick"]}#{name_link}'
            return f'wg://{proxy["server"]}:{proxy["port"]}?publicKey={proxy["wg_pub"]}&privateKey={proxy["wg_pk"]}=&presharedKey={proxy["wg_psk"]}&ip=10.0.0.1&mtu=1380&keepalive=30&udp=1&reserved=0,0,0&ifp={proxy["wg_noise_trick"]}#{name_link}'


    baseurl = f'{proxy["proto"]}://{proxy["uuid"]}@{proxy["server"]}:{proxy["port"]}'
    
    q = {
        'hiddify': 1,
        'sni': proxy['sni'],
        'type': proxy['transport'],
        'alpn': proxy['alpn']
    }

    # the ray2sing supports vless, vmess and trojan tls tricks and mux
    # the vmess handled already

    add_mux_to_dict(q,proxy)
    add_tls_tricks_to_dict(q,proxy)
    if "path" in proxy:
        q['path']=proxy["path"]
    if "host" in proxy :
        q['host']=proxy["host"]
    # infos+=f'&alpn={proxy["alpn"]}'
    
    if "grpc" == proxy["transport"]:
        q['serviceName']=proxy["grpc_service_name"]
        q['mode']=proxy["grpc_mode"]
    # print(proxy['cdn'],proxy["transport"])
    if request.args.get("fragment"):
        q['fragment']= request.args.get("fragment")  # type: ignore
    if "ws" == proxy["transport"] and proxy['cdn'] and request.args.get("fragment_v1"):
        q['fragment_v1']= request.args.get("fragment_v1")  # type: ignore
    if 'vless' == proxy['proto']:
        q['encryption']='none'

    if proxy.get('fingerprint', 'none') != 'none':
        q['fp']=proxy['fingerprint']
    if proxy.get('transport') in {ProxyTransport.xhttp}:
        q['core']='xray'
        _add_xhttp_extra(q,proxy)
    if proxy['l3'] != 'quic':
        if proxy.get('params',{}).get('headers',{}).get("type",'')=='none' or proxy['l3'] != ProxyL3.http:
            q['headerType']='none'
        else:
            # if proxy.get('l3') != ProxyL3.reality and (proxy.get('transport') in {ProxyTransport.tcp, ProxyTransport.httpupgrade, ProxyTransport.xhttp}) and proxy['proto'] in [ProxyProto.vless, ProxyProto.trojan]:
            q['headerType']='http'
        
    if proxy['mode'] == 'Fake' or proxy['allow_insecure']:
        q['allowInsecure']='true'
        q['insecure']='true'
    if proxy.get('flow'):
        q['flow']=proxy["flow"]

    
    if 'reality' in proxy["l3"]:
        q['security']='reality'
        q['pbk']=proxy['reality_pbk']
        q['sid']=proxy['reality_short_id']

        
    elif 'tls' in proxy['l3'] or "quic" in proxy['l3']:
        q['security']='tls'
        
    elif proxy['l3'] == 'http':
        q['security']='none'
    if proxy.get('transport') not in {ProxyTransport.xhttp}:
        for k,v in proxy.get('params',{}).items():
            if k not in q and k!="download":
                q[k]=v
    return f"{baseurl}?{urlencode(q,quote_via=quote)}#{name_link}"


def make_v2ray_configs(domains: list[Domain], user: User, expire_days: int, ip_debug=None) -> str:
    res = []

    if hconfig(ConfigEnum.show_usage_in_sublink) and not g.user_agent.get('is_hiddify'):

        fake_ip_for_sub_link = datetime.datetime.now().strftime(f"%H.%M--%Y.%m.%d.time:%H%M")
        # if ua['app'] == "Fair1":
        #     res.append(f'trojan://1@{fake_ip_for_sub_link}?sni=fake_ip_for_sub_link&security=tls#{round(user.current_usage_GB,3)}/{user.usage_limit_GB}GB_Remain:{expire_days}days')
        # else:

        # res.append(f'trojan://1@{fake_ip_for_sub_link}?sni=fake_ip_for_sub_link&security=tls#{hutils.encode.url_encode(profile_title)}')

        name = '⏳ ' if user.is_active else '✖ '
        if user.usage_limit_GB < 1000:
            name += f'{round(user.current_usage_GB,3)}/{str(user.usage_limit_GB).replace(".0","")}GB'
        elif user.usage_limit_GB < 100000:
            name += f'{round(user.current_usage_GB/1000,3)}/{str(round(user.usage_limit_GB/1000,1)).replace(".0","")}TB'
        else:
            res.append("#No Usage Limit")
        name += " 📅 "
        if expire_days < 1000:
            name += _(f'%(expire_days)s days', expire_days=expire_days)
        else:
            res.append("#No Time Limit")

        name = name.strip()
        if len(name) > 3:
            res.append(f'trojan://1@{fake_ip_for_sub_link}?sni=fake_ip_for_sub_link&security=tls#{hutils.encode.url_encode(name)}')

    if g.user_agent.get('is_browser') and ip_debug:
        res.append(f'#Hiddify auto ip: {ip_debug}')

    if not user.is_active:

        if hconfig(ConfigEnum.lang) == 'fa':
            res.append('trojan://1@1.1.1.1#' + hutils.encode.url_encode('✖ بسته شما به پایان رسید'))
        else:
            res.append('trojan://1@1.1.1.1#' + hutils.encode.url_encode('✖ Package Ended'))
        return "\n".join(res)

    for pinfo in hutils.proxy.get_valid_proxies(domains):
        link = to_link(pinfo)
        if 'msg' not in link:
            res.append(link)
    return "\n".join(res)


def add_tls_tricks_to_dict(d: dict, proxy: dict):
    if proxy.get('tls_fragment_enable'):
        # if g.user_agent.get('is_shadowrocket'):
        #     d['fragment'] = f'1,{proxy["tls_fragment_size"]},{proxy["tls_fragment_sleep"]}'
        # else:

        d['fragment'] = f'{proxy["tls_fragment_size"]},{proxy["tls_fragment_sleep"]},tlshello'
        # if g.user_agent.get('is_streisand'):
        # else:
        #     d['fragment'] = f'tlshello,{proxy["tls_fragment_size"]},{proxy["tls_fragment_sleep"]}'

    if proxy.get("tls_mixed_case"):
        d['mc'] = 1
    if proxy.get("tls_padding_enable"):
        d['padsize'] = proxy["tls_padding_length"]


def add_mux_to_dict(d: dict, proxy):
    if not is_muxable_agent(proxy):
        return

    # according to github.com/hiddify/ray2sing/
    d['muxtype'] = proxy["mux_protocol"]
    d['muxmaxc'] = proxy["mux_max_connections"]
    d['mux'] = proxy['mux_min_streams']
    d['muxsmax'] = proxy["mux_max_streams"]
    d['muxpad'] = proxy["mux_padding_enable"]

    if proxy.get('mux_brutal_enable'):
        d['muxup'] = proxy["mux_brutal_up_mbps"]
        d['muxdown'] = proxy["mux_brutal_down_mbps"]


def _add_xhttp_extra(d:dict,proxy):
    from .xrayjson import _add_xhttp_details
    xhttp_dict={}
    _add_xhttp_details(xhttp_dict,proxy)
    d['extra']=json.dumps(xhttp_dict['xhttpSettings']['extra'],separators=(',', ':'))