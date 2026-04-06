"""Query run history and produce reports."""

from phone_farm.db import Database


class Reporter:
    """Generates reports from run history data."""

    def __init__(self, *, db: Database) -> None:
        self.db = db

    async def summary(self) -> dict:
        """Overall summary: total accounts, runs, pass rate."""
        accounts = await self.db.list_accounts()
        total_runs = 0
        total_success = 0
        for acc in accounts:
            runs = await self.db.get_runs_for_account(acc["id"])
            total_runs += len(runs)
            total_success += sum(1 for r in runs if r["result"] == "success")

        return {
            "total_accounts": len(accounts),
            "total_runs": total_runs,
            "pass_rate": total_success / total_runs if total_runs > 0 else 0.0,
            "total_success": total_success,
            "total_failures": total_runs - total_success,
        }

    async def account_detail(self, email: str) -> dict:
        """Detailed report for a single account."""
        account = await self.db.get_account_by_email(email)
        if account is None:
            raise ValueError(f"Account not found: {email}")
        runs = await self.db.get_runs_for_account(account["id"])
        success_count = sum(1 for r in runs if r["result"] == "success")
        return {
            "email": email,
            "status": account["status"],
            "total_runs": len(runs),
            "success_count": success_count,
            "fail_count": len(runs) - success_count,
            "last_run": runs[0]["run_date"] if runs else None,
            "recent_errors": [
                r["error_log"] for r in runs[:5] if r["error_log"]
            ],
        }
