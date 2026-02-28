import pytest
from django.utils import timezone
from unittest.mock import patch
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from DataBuilder.models import Shop, Brand, Product, Receipt, CartItem

User = get_user_model()


@pytest.fixture
def setup_db_data(db):
    user = User.objects.create_user(username="testadmin", password="password123")

    shop = Shop.objects.create(name="Тестовий Магазин")
    brand = Brand.objects.create(name="Тестовий Бренд")
    product = Product.objects.create(name="Тестовий Товар", brand=brand)

    receipt = Receipt.objects.create(
        shop=shop, datetime=timezone.now(), total_price=150.00, margin_price_total=30.00, refund=False
    )

    CartItem.objects.create(
        receipt=receipt,
        product=product,
        datetime=timezone.now(),
        price=75.00,
        original_price=75.00,
        qty=2,
        total_price=150.00,
        margin_price_total=30.00,
    )
    return user


@pytest.fixture
def api_client(setup_db_data):
    client = APIClient()
    client.force_authenticate(user=setup_db_data)
    return client


@pytest.fixture
def base_payload():
    return {
        "metrics": ["turnover", "checks_count"],
        "group_by": ["shop_name"],
        "date_range": {"from_date": "2020-01-01", "to_date": "2026-12-31"},
    }


@pytest.mark.django_db
def test_analytics_returns_json_default(api_client, base_payload):
    response = api_client.post("/api/analytics/get-analytics/", base_payload, format="json")
    assert response.status_code == 200
    assert "data" in response.json()


@pytest.mark.django_db
def test_analytics_returns_chart_html(api_client, base_payload):
    payload = base_payload.copy()
    payload["render_type"] = "chart"
    payload["chart_type"] = "Bar Chart"

    response = api_client.post("/api/analytics/get-analytics/", payload, format="json")
    assert response.status_code == 200
    assert b"plotly" in response.content


@pytest.mark.django_db
@patch("DataBuilder.tasks.generate_and_send_chart_task.delay")
def test_analytics_triggers_chart_celery_task(mock_chart_task, api_client, base_payload):
    payload = base_payload.copy()
    payload["render_type"] = "chart"
    payload["email"] = "test@example.com"

    response = api_client.post("/api/analytics/get-analytics/", payload, format="json")
    assert response.status_code == 202
    mock_chart_task.assert_called_once()


@pytest.mark.django_db
@patch("DataBuilder.tasks.generate_and_send_excel_task.delay")
def test_analytics_triggers_excel_celery_task(mock_excel_task, api_client, base_payload):
    payload = base_payload.copy()
    payload["render_type"] = "excel"
    payload["email"] = "excel@example.com"

    response = api_client.post("/api/analytics/get-analytics/", payload, format="json")
    assert response.status_code == 202
    mock_excel_task.assert_called_once()
