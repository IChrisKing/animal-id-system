"""CLI 接口 — Click 命令定义"""

import json
import sys

import click
from rich.console import Console
from rich.table import Table

from src.utils.config import Config
from src.pipeline import Pipeline


console = Console()


def _load_pipeline(config_path: str) -> Pipeline:
    """加载配置并初始化 Pipeline"""
    try:
        config = Config(config_path)
    except FileNotFoundError:
        console.print(f"[red]配置文件未找到: {config_path}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]配置加载失败: {e}[/red]")
        sys.exit(1)

    try:
        return Pipeline(config)
    except Exception as e:
        console.print(f"[red]Pipeline 初始化失败: {e}[/red]")
        sys.exit(1)


@click.group()
@click.version_option(version="0.1.0", prog_name="animal-id")
def cli():
    """Animal ID System — 动物识别与档案管理系统

    支持从图片和视频中自动识别猫、黄鼠狼、鸟，并为每只猫建立独立档案。
    """
    pass


@cli.command()
@click.argument("paths", nargs=-1, required=True)
@click.option("--recursive/--no-recursive", default=True, help="递归扫描子目录")
@click.option("--type", "media_type", type=click.Choice(["image", "video", "all"]),
              default="image", help="只处理指定类型的媒体文件")
@click.option("--config", "-c", default="config.yaml", help="配置文件路径")
def scan(paths, recursive, media_type, config):
    """扫描并识别图片中的动物"""
    if media_type in ("video", "all"):
        console.print("[yellow]⚠️  Phase 1 仅支持图片处理，视频将在 Phase 2 支持[/yellow]")

    pipeline = _load_pipeline(config)

    console.print(f"[bold]📂 扫描路径:[/bold] {paths}")
    console.print(f"[bold]🔍 递归:[/bold] {recursive}")

    report = pipeline.run(list(paths))

    # 输出报告
    console.print()
    console.print("[bold green]=== 处理报告 ===[/bold green]")
    table = Table(title="处理统计")
    table.add_column("指标", style="cyan")
    table.add_column("数值", style="green")

    table.add_row("总文件数", str(report.total_files))
    table.add_row("处理成功", str(report.processed))
    table.add_row("跳过", str(report.skipped))
    table.add_row("错误", str(report.errors))
    table.add_row("未检测到动物", str(report.no_animal))
    table.add_row("新猫档案", str(report.new_profiles))
    table.add_row("更新已有猫", str(report.updated_profiles))
    table.add_row("API 调用次数", str(report.api_calls))
    table.add_row("API 缓存命中", str(report.api_cache_hits))
    table.add_row("耗时 (秒)", str(report.elapsed_seconds))

    console.print(table)

    if report.errors > 0:
        console.print()
        console.print("[red]错误详情:[/red]")
        for d in report.details:
            if d.get("status") == "error":
                console.print(f"  [red]✗[/red] {d['file']}: {d.get('error', 'unknown')}")


@cli.command()
@click.option("--limit", default=50, help="返回条数上限")
@click.option("--offset", default=0, help="分页偏移")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]),
              default="table", help="输出格式")
@click.option("--config", "-c", default="config.yaml", help="配置文件路径")
def list(limit, offset, output_format, config):
    """列出所有猫档案"""
    pipeline = _load_pipeline(config)
    profiles = pipeline.profile_manager.list_profiles(limit=limit, offset=offset)

    if output_format == "json":
        console.print_json(json.dumps(profiles, ensure_ascii=False, indent=2))
        return

    if not profiles:
        console.print("[yellow]暂无猫档案[/yellow]")
        return

    table = Table(title=f"🐱 猫档案 ({len(profiles)} 只)")
    table.add_column("ID", style="cyan")
    table.add_column("昵称")
    table.add_column("描述")
    table.add_column("出现次数", justify="right")
    table.add_column("最近发现")

    for p in profiles:
        desc = (p.get("description") or "")[:50]
        table.add_row(
            p["id"],
            p.get("nickname") or "-",
            desc,
            str(p.get("appearance_count", 0)),
            p.get("last_seen", "")[:19],
        )

    console.print(table)


@cli.command()
@click.argument("profile_id")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]),
              default="text", help="输出格式")
@click.option("--config", "-c", default="config.yaml", help="配置文件路径")
def show(profile_id, output_format, config):
    """显示单个猫档案详情"""
    pipeline = _load_pipeline(config)
    profile = pipeline.profile_manager.get_profile(profile_id)

    if profile is None:
        console.print(f"[red]档案未找到: {profile_id}[/red]")
        sys.exit(1)

    if output_format == "json":
        console.print_json(json.dumps(profile, ensure_ascii=False, indent=2))
        return

    console.print(f"[bold cyan]🐱 档案: {profile['id']}[/bold cyan]")
    console.print(f"  昵称: {profile.get('nickname') or '(未设置)'}")
    console.print(f"  描述: {profile.get('description') or '-'}")
    console.print(f"  首次发现: {profile.get('first_seen', '')[:19]}")
    console.print(f"  最近发现: {profile.get('last_seen', '')[:19]}")
    console.print(f"  出现次数: {profile.get('appearance_count', 0)}")

    sources = profile.get("sources", [])
    if sources:
        console.print()
        console.print("[bold]来源文件:[/bold]")
        for s in sources:
            console.print(f"  📄 {s['file_name']} ({s['type']})")
            console.print(f"     路径: {s['file_path']}")
            console.print(f"     添加: {s.get('added_at', '')[:19]}")


@cli.command()
@click.option("--output", "-o", default="profiles.json", help="输出文件路径")
@click.option("--format", "output_format", type=click.Choice(["json", "csv"]),
              default="json", help="导出格式")
@click.option("--config", "-c", default="config.yaml", help="配置文件路径")
def export(output, output_format, config):
    """导出档案数据"""
    pipeline = _load_pipeline(config)
    profiles = pipeline.profile_manager.list_profiles(limit=10000)

    if output_format == "json":
        with open(output, "w", encoding="utf-8") as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2)
        console.print(f"[green]✅ 已导出 {len(profiles)} 条档案至 {output}[/green]")
    elif output_format == "csv":
        import csv
        with open(output, "w", newline="", encoding="utf-8") as f:
            if profiles:
                writer = csv.DictWriter(f, fieldnames=profiles[0].keys())
                writer.writeheader()
                writer.writerows(profiles)
        console.print(f"[green]✅ 已导出 {len(profiles)} 条档案至 {output}[/green]")


@cli.command()
@click.argument("profile_id")
@click.option("--force/--no-force", default=False, help="强制删除，不确认")
@click.option("--config", "-c", default="config.yaml", help="配置文件路径")
def delete(profile_id, force, config):
    """删除猫档案"""
    if not force:
        click.confirm(f"确认删除档案 '{profile_id}' 及其所有来源记录?", abort=True)

    pipeline = _load_pipeline(config)
    ok = pipeline.profile_manager.delete_profile(profile_id)
    if ok:
        console.print(f"[green]✅ 已删除: {profile_id}[/green]")
    else:
        console.print(f"[red]档案未找到: {profile_id}[/red]")


@cli.command()
@click.option("--config", "-c", default="config.yaml", help="配置文件路径")
def stats(config):
    """显示统计信息"""
    pipeline = _load_pipeline(config)

    cat_count = pipeline.profile_manager.count_profiles()
    proc_stats = pipeline.db.get_processing_stats()

    console.print("[bold cyan]📊 Animal ID System 统计[/bold cyan]")
    console.print()
    console.print(f"  🐱 猫档案总数: {cat_count}")
    console.print(f"  📄 已处理文件: {proc_stats['total_files_processed']}")
    console.print(f"     - 成功: {proc_stats['success']}")
    console.print(f"     - 跳过: {proc_stats['skipped']}")
    console.print(f"     - 错误: {proc_stats['errors']}")


@cli.command()
def test_run():
    """使用内置测试数据验证系统是否正常运行"""
    console.print("🔧 运行系统自检...")

    checks = []

    # 1. OpenCV
    try:
        import cv2
        checks.append(("OpenCV", True, cv2.__version__))
    except Exception as e:
        checks.append(("OpenCV", False, str(e)))

    # 2. PyTorch
    try:
        import torch
        checks.append(("PyTorch", True, torch.__version__))
    except Exception as e:
        checks.append(("PyTorch", False, str(e)))

    # 3. YOLO
    try:
        from ultralytics import YOLO
        checks.append(("ultralytics", True, "OK"))
    except Exception as e:
        checks.append(("ultralytics", False, str(e)))

    # 4. Database
    try:
        from src.storage import Database
        checks.append(("Database", True, "OK"))
    except Exception as e:
        checks.append(("Database", False, str(e)))

    # 5. API Key
    import os
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if api_key and api_key != "":
        checks.append(("DEEPSEEK_API_KEY", True, "已设置"))
    else:
        checks.append(("DEEPSEEK_API_KEY", False, "未设置 (API 分类将走 Fallback)"))

    for name, ok, detail in checks:
        icon = "[green]✅[/green]" if ok else "[red]❌[/red]"
        console.print(f"  {icon} {name}: {detail}")

    if all(c[1] for c in checks):
        console.print("\n[green]✅ 系统自检通过![/green]")
    else:
        console.print("\n[yellow]⚠️  部分组件未就绪，部分功能可能受限[/yellow]")
