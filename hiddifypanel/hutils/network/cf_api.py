
from typing import TYPE_CHECKING
from hiddifypanel.models import hconfig, ConfigEnum
if TYPE_CHECKING:
    import cloudflare

__cf: "cloudflare.Cloudflare"=None   # type: ignore


def __prepare_cf_api_client() -> bool:
    import cloudflare

    '''Prepares cloudflare client if it's not already'''
    global __cf
    if __cf and isinstance(__cf, cloudflare.Cloudflare):
        return True

    if hconfig(ConfigEnum.cloudflare):
        __cf = cloudflare.Cloudflare(api_token=hconfig(ConfigEnum.cloudflare))
        if __cf and isinstance(__cf, cloudflare.Cloudflare):
            return True
    return False


def add_or_update_dns_record(domain: str, ip: str, dns_type: str = "A", proxied: bool = True) -> bool:
    '''This function cloud throw an exception'''
    if not __prepare_cf_api_client():
        return False

    zone_name = __extract_root_domain(domain)
    zone = __get_zone(zone_name)
    if zone:
        record = __get_dns_record(zone, domain,dns_type)
        dns_name = domain[:-len(zone.name)].replace('.', '')
        # if the input domain is root itself
        dns_name = '@' if not dns_name else dns_name
        
        if not record:
            api_res = __cf.dns.records.create(zone_id=zone.id, name=dns_name,type=dns_type,content=ip,proxied=proxied)
        else:
            api_res = __cf.dns.records.edit(zone_id=zone.id,dns_record_id= record.id, name=dns_name,type=dns_type,content=ip,proxied=proxied)

        # validate api response
        if api_res.name == domain and api_res.type == dns_type and api_res.content == ip:
            return True
    return False


def delete_dns_record(domain: str) -> bool:
    '''Deletes a DNS record from cloudflare panel of user'''
    if not __prepare_cf_api_client():
        return False

    zone_name = __extract_root_domain(domain)
    zone = __get_zone(zone_name)
    records = [__get_dns_record(zone, domain,"A"),__get_dns_record(zone, domain,"AAAA")]
    res=False
    
    for record in records:
        if record and zone:
            api_res = __cf.dns.records.delete(dns_record_id=record.id,zone_id=zone.id)
            if api_res.id == record.id:
                res=True
            
    return res


def __get_zone(zone_name: str):
    zones = __cf.zones.list()
    for z in zones:
        if z.name == zone_name:
            return z
    return None


def __get_dns_record(zone, domain: str,dns_type) :
    '''Returns dns record if exists'''
    dns_records = __cf.dns.records.list(zone_id=zone.id)#__cf.zones.get(zone['id']).dns_records(zone['id'])
    for r in dns_records:
        if r.name == domain and r.type==dns_type:
            return r
    return None


def __extract_root_domain(domain: str) -> str:
    domain_parts = domain.split(".")
    if len(domain_parts) > 1:
        return ".".join(domain_parts[-2:])
    else:
        return domain
