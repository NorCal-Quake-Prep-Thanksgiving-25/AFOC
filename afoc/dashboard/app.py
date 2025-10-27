"""Streamlit dashboard entry point."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from afoc.services import forecasting, rightsizing, valuation


def _sample_usage(days: int = 60) -> list[dict]:
    base = datetime.utcnow() - timedelta(days=days)
    records: list[dict] = []
    for offset in range(days):
        ts = base + timedelta(days=offset)
        cost = 200 + 12 * ((offset % 7) - 3) + 6 * ((offset % 30) - 15) / 5
        records.append({"date": ts, "account": "demo", "cost_usd": float(cost)})
    return records


def _sample_inventory() -> tuple[list[dict], list[dict]]:
    inventory = [
        {
            "resource_id": "demo-instance",
            "instance_type": "m5.large",
            "price": 0.12,
            "cpu_capacity": 2.0,
            "memory_capacity": 8.0,
            "metadata": {
                "options": [
                    {
                        "instance_type": "t3.medium",
                        "price": 0.067,
                        "cpu_capacity": 2.0,
                        "memory_capacity": 4.0,
                    }
                ]
            },
        }
    ]
    utilization = [{"resource_id": "demo-instance", "p95_cpu": 32.0, "p95_mem": 35.0}]
    return inventory, utilization


def main() -> None:
    """Render the AFOC dashboard with sample data."""

    st.title("AFOC Insight Console")
    st.caption("Autonomous Fiscal Orchestration Core – sample insights")

    overview_tab, rightsizing_tab, forecast_tab, proof_tab = st.tabs(
        ["Overview", "Right-Sizing", "Forecast", "Proof"]
    )

    with overview_tab:
        st.write(
            "This demo streams synthetic data through the forecasting and rightsizing"
            " engines before generating a valuation proof."
        )

    inventory, utilization = _sample_inventory()
    recs = rightsizing.generate_recommendations(inventory, utilization)
    with rightsizing_tab:
        if recs:
            st.subheader("Right-Sizing Recommendations")
            st.dataframe(pd.DataFrame(recs))
        else:
            st.info("No right-sizing opportunities detected")

    usage_records = _sample_usage()
    forecast_result = forecasting.generate_forecast(
        usage_records, scope="demo", horizon=30
    )
    with forecast_tab:
        forecast_df = pd.DataFrame(forecast_result.to_dict()["points"])
        if not forecast_df.empty:
            forecast_df["ds"] = pd.to_datetime(forecast_df["ds"])
            forecast_df.set_index("ds", inplace=True)
            st.subheader("Spend Forecast")
            st.line_chart(forecast_df[["yhat"]])
            if forecast_result.mape is not None:
                st.caption(f"MAPE: {forecast_result.mape:.2f}%")
        else:
            st.info("Insufficient data for forecasting")

    with proof_tab:
        rightsizing_savings = sum(
            max(
                float(item.get("current_price", 0.0))
                - float(item.get("recommended_price", 0.0)),
                0.0,
            )
            for item in recs
        )
        inputs = valuation.ValueInputs(
            annual_spend=1_000_000,
            anomaly_spend=50_000,
            rightsizing_monthly_savings=rightsizing_savings,
            reservable_spend=120_000,
            tier="mid",
            anomaly_count=3,
        )
        report = valuation.compute_value_report(inputs)
        st.metric("Integrated Value", f"${report.integrated:,.2f}")
        st.write("Anomaly value:", f"${report.anomaly:,.2f}")
        st.write("Right-sizing value:", f"${report.rightsize:,.2f}")
        st.write("Forecast value:", f"${report.forecast:,.2f}")
        st.json(report.assumptions)


if __name__ == "__main__":
    main()
