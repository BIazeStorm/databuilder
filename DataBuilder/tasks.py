import pandas as pd
from io import BytesIO
from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings

from .services import AnalyticsService
from .serializers import AnalyticsRequestSerializer


@shared_task
def generate_and_send_excel_task(request_data: dict):
    serializer = AnalyticsRequestSerializer(data=request_data)
    serializer.is_valid(raise_exception=True)
    params = serializer.validated_data

    group_by = params.get("group_by", [])
    metrics = params.get("metrics", [])
    include_total = params.get("total", False)
    current_range = params["date_range"]
    prev_range = params.get("prev_date_range")
    email_to = params.get("email")

    service = AnalyticsService(dimensions=group_by, metrics=metrics)

    if prev_range:
        df = service.get_comparison_dataframe(current_range, prev_range)
        total_df = (
            service.get_comparison_dataframe(current_range, prev_range, as_total=True)
            if include_total
            else pd.DataFrame()
        )
    else:
        df = service.get_dataframe(current_range["from_date"], current_range["to_date"])
        total_df = (
            service.get_dataframe(current_range["from_date"], current_range["to_date"], as_total=True)
            if include_total
            else pd.DataFrame()
        )

    excel_file = BytesIO()
    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        if not df.empty:
            df.to_excel(writer, sheet_name="Analytics", index=False)
        if include_total and not total_df.empty:
            total_df.to_excel(writer, sheet_name="Total", index=False)

    excel_file.seek(0)

    subject = "Аналітичний звіт (DataBuilder)"
    body = "Привіт! Твій звіт у форматі Excel готовий. Файл прикріплено до цього листа."

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,  # Або вкажи тут свою адресу, наприклад 'noreply@databuilder.com'
        to=[email_to],
    )

    email.attach(
        "analytics_report.xlsx", excel_file.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    email.send()

    return f"Report sent to {email_to}"


@shared_task
def generate_and_send_chart_task(request_data, email):
    serializer = AnalyticsRequestSerializer(data=request_data)
    serializer.is_valid(raise_exception=True)
    params = serializer.validated_data

    service = AnalyticsService(dimensions=params.get("group_by", []), metrics=params.get("metrics", []))

    current_range = params.get("date_range")
    prev_range = params.get("prev_date_range")

    if prev_range:
        df = service.get_comparison_dataframe(current_range=current_range, prev_range=prev_range)
    else:
        df = service.get_dataframe(date_from=current_range["from_date"], date_to=current_range["to_date"])

    chart_type = params.get("chart_type", "Bar Chart")
    html_content = service.generate_plotly_chart(df, chart_type)

    email_msg = EmailMessage(
        subject=f"Аналітичний звіт ({chart_type})",
        body="Звіт згенеровано. Інтерактивний графік у вкладенні.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    email_msg.attach("analytics_report.html", html_content, "text/html")
    email_msg.send()
