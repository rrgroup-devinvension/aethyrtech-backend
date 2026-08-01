import pytest
import responses

from experience_cloud.api_provider.tests.factories import ApiProviderFactory
from experience_cloud.market_integrations.clients.xbyte_client import XByteClient


@pytest.mark.django_db
class TestXByteClient:
    """Test suite for the XByte external market integration client."""

    @responses.activate
    def test_xbytes_fetch_results(self):
        """Test XByte data fetching intercepts HTTP calls via responses library."""
        # 1. ARRANGE
        # The BaseApiClient looks for an ApiProvider with the given code
        ApiProviderFactory(
            code="XBYTE",
            base_url="https://api.xbytes.fake.com"
        )

        # Mock the external API response
        responses.add(
            responses.POST,
            "https://api.xbytes.fake.com",
            json={"results": [{"id": 123, "price": 99.99}]},
            status=200
        )

        client = XByteClient(provider_code="XBYTE")

        # 2. ACT
        result = client.fetch_results(keyword="laptop", location="10001", platform="AMAZON")

        # 3. ASSERT
        assert result['results'][0]['price'] == 99.99
        assert len(responses.calls) == 1
