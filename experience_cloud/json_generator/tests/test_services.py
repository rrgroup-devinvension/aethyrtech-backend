from unittest.mock import patch


class TestJsonGeneratorService:
    """Test suite for JsonGeneratorService."""

    @patch('experience_cloud.json_generator.tasks.process_region_batch')
    def test_json_tree_builder_mocked(self, mock_build):
        """Test the celery task is mocked properly."""
        # 1. ARRANGE
        mock_build.return_value = {"status": "success"}

        # 2. ACT
        result = mock_build(execution_id=1, region_id=1, file_task_ids=[1])

        # 3. ASSERT
        mock_build.assert_called_once_with(execution_id=1, region_id=1, file_task_ids=[1])
        assert result['status'] == 'success'
