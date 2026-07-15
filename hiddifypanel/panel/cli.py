import datetime
import uuid
import json
import os
import click
from dateutil import relativedelta


from hiddifypanel import hutils

from hiddifypanel.models import *
from hiddifypanel.panel import hiddify, usage
from hiddifypanel.database import db
from hiddifypanel.panel.init_db import init_db

from loguru import logger


def drop_db():
    """Cleans database"""
    db.drop_all()


def downgrade():
    if hconfig(ConfigEnum.db_version) >= "49":
        set_hconfig(ConfigEnum.db_version, "42", commit=False)
        StrConfig.query.filter(
            StrConfig.key.in_([ConfigEnum.tuic_enable, ConfigEnum.tuic_port, ConfigEnum.hysteria_enable, ConfigEnum.hysteria_port, ConfigEnum.ssh_server_enable, ConfigEnum.ssh_server_port, ConfigEnum.ssh_server_redis_url])
        ).delete()
        Proxy.query.filter(Proxy.l3.in_([ProxyL3.ssh, ProxyL3.h3_quic, ProxyL3.custom])).delete()
        db.session.commit()
        os.rename("/opt/hiddify-manager/hiddify-panel/hiddifypanel.db.old", "/opt/hiddify-manager/hiddify-panel/hiddifypanel.db")


from celery import shared_task


def backup():
    backup_task()


@shared_task(ignore_result=False)
def backup_task():
    dbdict = hiddify.dump_db_to_dict()
    os.makedirs("backup", exist_ok=True)
    dst = f"backup/{datetime.datetime.now().strftime('%Y_%m_%d__%H_%M_%S')}.json"
    with open(dst, "w", encoding="utf-8") as fp:
        json.dump(dbdict, fp, indent=2, sort_keys=True, default=str)
    print(dst)
    if hconfig(ConfigEnum.telegram_bot_token):
        from hiddifypanel.panel.commercial.telegrambot import bot, register_bot

        if not bot.username:
            register_bot(True)

        for admin in db.session.query(AdminUser).filter(AdminUser.mode == AdminMode.super_admin, AdminUser.telegram_id is not None, AdminUser.telegram_id != 0).all():
            caption = "Backup \n" + admin_links()
            with open(dst, "rb") as document:
                try:
                    bot.send_document(admin.telegram_id, document, visible_file_name=dst.replace("backup/", ""), caption=caption[:1000])
                except Exception as e:
                    logger.exception(e)


def all_configs():
    print(json.dumps(hiddify.all_configs_for_cli(), indent=4))


def update_usage():
    print(usage.update_local_usage())


def admin_links():
    server_ip = hutils.network.get_ip_str(4)
    owner = AdminUser.get_super_admin()

    admin_links = f"Not Secure (do not use it - only if others not work):\n   {hiddify.get_account_panel_link(owner, server_ip, is_https=True)}\n"

    domains = Domain.get_domains()
    admin_links += f"Secure:\n"
    if not any([d for d in domains if "sslip.io" not in d.domain]):
        admin_links += f"   (not signed) {hiddify.get_account_panel_link(owner, server_ip)}\n"

    for d in domains:
        admin_links += f"   {hiddify.get_account_panel_link(owner, d.domain)}\n"

    print(admin_links)
    return admin_links


def admin_path():
    admin = AdminUser.get_super_admin()
    # WTF is the owner and server_id?
    domain = Domain.get_domains()[0]
    print(hiddify.get_account_panel_link(admin, domain, prefere_path_only=True))


def hysteria_domain_port():
    if not hconfig(ConfigEnum.hysteria_enable):
        return
    out = []
    for domain in Domain.query.filter(
        Domain.mode.in_([DomainType.direct, DomainType.relay]),
        Domain.fake_mode != FakeMode.reality,
    ).all():
        out.append(f"{domain.domain}:{int(hconfig(ConfigEnum.hysteria_port)) + domain.id}")
    print(";".join(out))


def tuic_domain_port():
    if not hconfig(ConfigEnum.tuic_enable):
        return
    out = []
    for domain in Domain.query.filter(
        Domain.mode.in_([DomainType.direct, DomainType.relay]),
        Domain.fake_mode != FakeMode.reality,
    ).all():
        out.append(f"{domain}:{int(hconfig(ConfigEnum.tuic_port)) + domain.id}")
    print(";".join(out))


def init_app(app):
    for command in [hysteria_domain_port, tuic_domain_port, init_db, drop_db, all_configs, update_usage, admin_links, admin_path, backup, downgrade]:
        app.cli.add_command(app.cli.command()(command))

    @app.cli.command()
    @click.option("--domain", "-d")
    @click.option("--mode", "-m")
    def add_domain(domain, mode):
        if Domain.query.filter(Domain.domain == domain).first():
            return "Domain already exist."
        d = Domain()
        d.domain = domain
        d.mode = mode
        d.sub_link_only = True if mode == DomainType.sub_link_only else False
        db.session.add(d)
        db.session.commit()
        return "success"

    @app.cli.command()
    @click.option("--admin_secret", "-a")
    def set_admin_secret(admin_secret):
        StrConfig.query.filter(StrConfig.key == ConfigEnum.admin_secret).update({"value": admin_secret})
        db.session.commit()
        return "success"

    @app.cli.command()
    @click.option("--key", "-k")
    @click.option("--val", "-v")
    def set_setting(key, val):
        old_hconfigs = get_hconfigs()
        hiddify.add_or_update_config(key=key, value=val)

        return "success"

    @app.cli.command("get-setting")
    @click.argument("key")
    @click.option("--child-id", "-c", default=0, show_default=True, type=int)
    def get_setting_cmd(key, child_id):
        from hiddifypanel.panel.setting_cli import get_setting_from_db

        value = get_setting_from_db(key, child_id)
        if not value:
            raise click.ClickException(f"Setting not found: {key}")
        click.echo(value, nl=False)

    @app.cli.command()
    def reset_owner_password():
        AdminUser.get_super_admin().update_password("")
        return "success"

    @app.cli.command()
    @click.option("--config", "-c")
    def import_config(config):
        next10year = datetime.date.today() + relativedelta.relativedelta(years=10)
        data = []
        if "USER_SECRET" in config:
            secrets = config["USER_SECRET"].split(";")
            for i, s in enumerate(secrets):
                data.append(User(name=f"default {i}", uuid=uuid.UUID(s), usage_limit_GB=9000, package_days=3650))

        if "MAIN_DOMAIN" in config:
            domains = config["MAIN_DOMAIN"].split(";")
            for i, d in enumerate(domains):
                if not Domain.query.filter(Domain.domain == d).first():
                    data.append(
                        Domain(domain=d, mode=DomainType.direct),
                    )

        strmap = {
            "TELEGRAM_FAKE_TLS_DOMAIN": ConfigEnum.telegram_fakedomain,
            "TELEGRAM_SECRET": ConfigEnum.shared_secret,
            "SS_FAKE_TLS_DOMAIN": ConfigEnum.ssfaketls_fakedomain,
            "FAKE_CDN_DOMAIN": ConfigEnum.domain_fronting_domain,
            "BASE_PROXY_PATH": ConfigEnum.proxy_path,
            "ADMIN_SECRET": ConfigEnum.admin_secret,
            "TELEGRAM_AD_TAG": ConfigEnum.telegram_adtag,
        }
        boolmap = {
            "ENABLE_SS": ConfigEnum.ssfaketls_enable,
            "ENABLE_TELEGRAM": ConfigEnum.telegram_enable,
            "ENABLE_VMESS": ConfigEnum.vmess_enable,
            # "ENABLE_MONITORING":ConfigEnum.ssfaketls_enable,
            "ENABLE_FIREWALL": ConfigEnum.firewall,
            "ENABLE_NETDATA": ConfigEnum.netdata,
            "ENABLE_HTTP_PROXY": ConfigEnum.http_proxy_enable,
            "ALLOW_ALL_SNI_TO_USE_PROXY": ConfigEnum.allow_invalid_sni,
            "ENABLE_AUTO_UPDATE": ConfigEnum.auto_update,
            "ENABLE_SPEED_TEST": ConfigEnum.speed_test,
            "BLOCK_IR_SITES": ConfigEnum.block_iran_sites,
            "ONLY_IPV4": ConfigEnum.only_ipv4,
        }

        for k in config:
            if k in strmap:
                if hconfig(strmap[k]) is None:
                    data.append(StrConfig(key=strmap[k], value=config[k]))
                else:
                    StrConfig.query.filter(StrConfig.key == strmap[k]).update({"value": config[k]})
            if k in boolmap:
                if hconfig(boolmap[k]) is None:
                    data.append(BoolConfig(key=boolmap[k], value=config[k]))
                else:
                    BoolConfig.query.filter(BoolConfig.key == strmap[k]).update({"value": config[k]})
        if len(data):
            db.session.bulk_save_objects(data)
        db.session.commit()

    @app.cli.command()
    @click.option("--xui_db_path", "-x")
    def xui_importer(xui_db_path):
        try:
            hutils.importer.xui.import_data(xui_db_path)
            print("success")
        except Exception as e:
            print(f"failed to import xui data: Error: {e}")

    def _run_sync_builtin_catalog(child_id: int) -> None:
        from hiddifypanel.proxy_v3.builtin_proxy_sync.orchestrator import sync_all as sync_builtin_catalog

        stats = sync_builtin_catalog(child_id)
        click.echo(f"synced builtin catalog (child_id={stats.child_id}): {stats.builtin_templates} templates, {stats.builtin_base_configs} base configs, {stats.builtin_custom_proxies} custom proxies")

    @app.cli.command("sync-builtin-configs")
    @click.option("--child-id", "-c", default=0, show_default=True, type=int)
    def sync_builtin_configs(child_id):
        """Refresh builtin proxy templates, base configs, and preset rows from disk."""
        _run_sync_builtin_catalog(child_id)

    @app.cli.command("sync-builtin-proxies")
    @click.option("--child-id", "-c", default=0, show_default=True, type=int)
    def sync_builtin_proxies(child_id):
        """Alias for sync-builtin-configs."""
        _run_sync_builtin_catalog(child_id)

    @app.cli.command("sync-tls-store")
    @click.option("--domain", "-d", default=None, help="Sync by domain hostname")
    @click.option("--domain-id", default=None, type=int, help="Sync by domain.id")
    @click.option("--child-id", "-c", default=0, show_default=True, type=int)
    def sync_tls_store(domain, domain_id, child_id):
        """Import TLS certificates from /opt/hiddify-manager/ssl/ into tls_store."""
        from hiddifypanel.proxy_v3.tls_store_sync import (
            sync_tls_store_all,
            sync_tls_store_for_domain,
            sync_tls_store_for_domain_id,
        )

        if domain_id is not None:
            row = sync_tls_store_for_domain_id(domain_id)
            if row:
                host = row.domain.domain if row.domain else domain_id
                click.echo(f"synced certificate for domain_id={row.domain_id} ({host}) issuer={row.issuer}")
            else:
                click.echo(f"no certificate files found for domain_id={domain_id}", err=True)
            return
        if domain:
            row = sync_tls_store_for_domain(domain, child_id=child_id)
            if row:
                host = row.domain.domain if row.domain else domain
                click.echo(f"synced certificate for domain_id={row.domain_id} ({host}) issuer={row.issuer}")
            else:
                click.echo(f"no certificate files found for {domain}", err=True)
            return
        count = sync_tls_store_all(child_id)
        click.echo(f"synced {count} tls_store row(s)")

    @app.cli.command("reset-wip-proxy-db")
    @click.option("--child-id", "-c", default=0, show_default=True, type=int)
    def reset_wip_proxy_db(child_id):
        """Drop WIP proxy/TLS tables and set db_version=129 for fresh _v130 migration."""
        from hiddifypanel.models import ConfigEnum, set_hconfig
        from hiddifypanel.panel.init_db import _drop_wip_proxy_tables

        _drop_wip_proxy_tables()
        set_hconfig(ConfigEnum.db_version, 129, child_id=child_id, commit=True)
        click.echo("WIP tables dropped; db_version set to 129. Restart panel to run _v130.")

    @app.cli.command("generate-example-configs")
    @click.option("--output", "output", type=click.Path(), default=None)
    @click.option("--child-id", "-c", default=0, show_default=True, type=int)
    @click.option("--domain", default="94.242.53.78.sslip.io", show_default=True)
    @click.option("--ip", default="94.242.53.78", show_default=True)
    @click.option("--user-uuid", default="1c26bc0e-6dc4-4fd9-819e-2540c46b9edf", show_default=True)
    @click.option("--refresh-db", is_flag=True, help="Rebuild local sqlite catalog from disk")
    def generate_example_configs(output, child_id, domain, ip, user_uuid, refresh_db):
        """Write bundled client/server configs to examples/new/."""
        import sys
        from pathlib import Path

        examples_dir = Path(__file__).resolve().parents[3] / "examples"
        if str(examples_dir) not in sys.path:
            sys.path.insert(0, str(examples_dir))
        from generate_examples import EXAMPLES_ROOT, generate_configs

        out = output or (EXAMPLES_ROOT / "new")
        result = generate_configs(
            output_root=Path(out),
            child_id=child_id,
            domain=domain,
            ip=ip,
            user_uuid=user_uuid,
            refresh_db=refresh_db,
        )
        for rel, size in sorted(result["written"].items()):
            click.echo(f"wrote {rel} ({size} bytes)")
        for item in result["missing"]:
            click.echo(f"missing {item}", err=True)
        for err in result["errors"]:
            click.echo(f"error: {err.get('message', err)}", err=True)
        if not result["ok"] or result["missing"]:
            raise SystemExit(1)

    @app.cli.command("dump-hiddify-core-server-config")
    @click.option("--output", "-o", type=click.Path(), default=None, help="Write config to file (default: stdout)")
    @click.option("--child-id", "-c", default=0, show_default=True, type=int)
    @click.option("--refresh-db", is_flag=True, help="Sync builtin proxy catalog from disk before rendering")
    @click.option("--compact", is_flag=True, help="Emit compact JSON instead of indented output")
    def dump_hiddify_core_server_config(output, child_id, refresh_db, compact):
        """Render and dump the hiddify-core server sing-box config."""
        from hiddifypanel.proxy_v3.config_builder.dump import (
            dump_hiddify_core_server_config as render_dump,
            format_builder_messages,
        )

        if refresh_db:
            _run_sync_builtin_catalog(child_id)

        rendered, result = render_dump(child_id, pretty=not compact)
        for message in format_builder_messages(result):
            level = message.get("level", "info")
            text = message.get("message", "")
            click.echo(f"{level}: {text} {message.get('data', '')}", err=True)

        if output:
            os.makedirs(os.path.dirname(output), exist_ok=True)
            with open(output, "w", encoding="utf-8") as fp:
                fp.write(rendered)
                if rendered and not rendered.endswith("\n"):
                    fp.write("\n")
            click.echo(f"wrote {output}")
        else:
            click.echo(rendered, nl=False)
            if rendered and not rendered.endswith("\n"):
                click.echo()

        if result.messages:
            raise SystemExit(1)

    @app.cli.command("dump-server-configs")
    @click.argument("output_dir", type=click.Path(file_okay=False, dir_okay=True, writable=True))
    @click.option("--child-id", "-c", default=0, show_default=True, type=int)
    @click.option("--refresh-db", is_flag=True, help="Sync builtin proxy catalog from disk before rendering")
    @click.option("--compact", is_flag=True, help="Emit compact JSON instead of indented output")
    def dump_server_configs(output_dir, child_id, refresh_db, compact):
        """Render and write xray, hiddify-core, haproxy, and nginx server configs to a directory."""
        from pathlib import Path

        from hiddifypanel.proxy_v3.config_builder.dump import dump_all_server_configs

        if refresh_db:
            _run_sync_builtin_catalog(child_id)

        result = dump_all_server_configs(output_dir, child_id, pretty=not compact)
        for filename, size in sorted(result.written.items()):
            click.echo(f"wrote {Path(output_dir) / filename} ({size} bytes)")
        for item in result.messages:
            level = item.get("level", "info")
            core = item.get("core", "")
            text = item.get("message", "")
            click.echo(f"{level}: [{core}] {text}", err=level == "error")
            data = item.get("data") or {}
            if level == "error" and data.get("stacktrace"):
                click.echo(data["stacktrace"], err=True)
        if not result.ok:
            raise SystemExit(1)

    @app.cli.command()
    def tgbot_info():
        if not hconfig(ConfigEnum.telegram_bot_token):
            print("You didn't specified your telegram bot token")
            return

        from hiddifypanel.panel.commercial.telegrambot import bot, register_bot

        if not bot.username:
            register_bot(True)
        info = bot.get_me().to_dict()
        hook_data = bot.get_webhook_info()
        hook_info = {
            "url": hook_data.url,
            "ip": hook_data.ip_address,
            "last_error_msg": hook_data.last_error_message if hook_data.last_error_message else "",
            "last_error_time": datetime.datetime.fromtimestamp(int(hook_data.last_error_date)).strftime("%Y-%m-%d %H:%M:%S") if hook_data.last_error_date else "",
        }

        output = {"general": info, "webhook": hook_info}
        print(json.dumps(output, indent=4))
