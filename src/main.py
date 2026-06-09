"""Animal ID System — 动物识别与档案管理系统入口"""

import sys
from src.cli import cli


def main():
    """主入口"""
    try:
        cli()
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 未捕获的异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
