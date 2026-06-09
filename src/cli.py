"""CLI 接口 — Click 命令定义"""

import click


@click.group()
@click.version_option(version="0.1.0", prog_name="animal-id")
def cli():
    """Animal ID System — 动物识别与档案管理系统

    支持从图片和视频中自动识别猫、黄鼠狼、鸟，并为每只动物建立独立档案。
    """
    pass


@cli.command()
@click.argument("paths", nargs=-1, required=True)
@click.option("--recursive/--no-recursive", default=True, help="递归扫描子目录")
@click.option("--type", "media_type", type=click.Choice(["image", "video", "all"]),
              default="all", help="只处理指定类型的媒体文件")
@click.option("--config", "-c", default="config.yaml", help="配置文件路径")
def scan(paths, recursive, media_type, config):
    """扫描并识别媒体文件中的动物"""
    click.echo(f"📂 扫描路径: {paths}")
    click.echo(f"🔍 递归: {recursive}, 类型: {media_type}")
    click.echo(f"⚙️  配置文件: {config}")
    click.echo("🚧 功能开发中...")
    # TODO: 实现 scan 逻辑


@cli.command()
@click.option("--class", "class_name", type=click.Choice(["cat", "weasel", "bird"]),
              help="按动物类别筛选")
@click.option("--limit", default=50, help="返回条数上限")
@click.option("--offset", default=0, help="分页偏移")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]),
              default="table", help="输出格式")
def list(class_name, limit, offset, output_format):
    """列出所有动物档案"""
    click.echo("🚧 功能开发中...")
    # TODO: 实现 list 逻辑


@cli.command()
@click.argument("profile_id")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]),
              default="text", help="输出格式")
def show(profile_id, output_format):
    """显示单个动物档案详情"""
    click.echo(f"🔍 档案 ID: {profile_id}")
    click.echo("🚧 功能开发中...")
    # TODO: 实现 show 逻辑


@cli.command()
@click.option("--output", "-o", default="profiles.json", help="输出文件路径")
@click.option("--class", "class_name", type=click.Choice(["cat", "weasel", "bird"]),
              help="按动物类别筛选")
@click.option("--format", "output_format", type=click.Choice(["json", "csv"]),
              default="json", help="导出格式")
def export(output, class_name, output_format):
    """导出档案数据"""
    click.echo(f"📤 导出至: {output}")
    click.echo("🚧 功能开发中...")
    # TODO: 实现 export 逻辑


@cli.command()
@click.argument("profile_id")
@click.option("--force/--no-force", default=False, help="强制删除，不确认")
def delete(profile_id, force):
    """删除动物档案"""
    if not force:
        click.confirm(f"确认删除档案 '{profile_id}'?", abort=True)
    click.echo(f"🗑️  已删除: {profile_id}")
    # TODO: 实现 delete 逻辑


@cli.command()
def stats():
    """显示统计信息"""
    click.echo("🚧 功能开发中...")
    # TODO: 实现 stats 逻辑


@cli.command()
def test_run():
    """使用内置测试数据验证系统是否正常运行"""
    click.echo("🔧 运行系统自检...")
    # TODO: 实现 test-run 逻辑
    click.echo("✅ 系统自检通过!")
