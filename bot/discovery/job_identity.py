from bot.utils.logger import logger

class JobIdentity:
    @staticmethod
    async def extract_job_id(element):
        """
        Extracts job ID from a job card element (Playwright locator).
        Tries 'data-job-id' attribute explicitly.
        """
        try:
            job_id = await element.get_attribute("data-job-id")
            if job_id:
                return job_id
            
            # Fallback parsing if needed
            # Usually data-job-id is reliable on LinkedIn search results
            
            return None
        except Exception as e:
            logger.debug(f"Failed to extract job ID: {e}", step="extract_job_id")
            return None
