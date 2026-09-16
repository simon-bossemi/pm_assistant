import sys


def main() -> int:
    print(
        "SMTP sending is deprecated in this workspace. "
        "Use .\\send-email.ps1 to create or send mail through Outlook desktop.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
