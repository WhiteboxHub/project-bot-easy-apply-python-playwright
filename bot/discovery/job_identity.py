from bot.utils.logger import logger

class JobIdentity:
    @staticmethod
    def extract_job_id(element):
        """
        Extracts job ID from a job card element (Playwright locator).
        Tries multiple methods with short timeouts.
        """
        try:
            # Method 1: Try data-job-id attribute with short timeout
            try:
                job_id = element.get_attribute("data-job-id", timeout=2000)
                if job_id:
                    return job_id
            except:
                pass
            
            # Method 2: Try data-occludable-job-id attribute
            try:
                job_id = element.get_attribute("data-occludable-job-id", timeout=2000)
                if job_id:
                    # Extract just the number part (format: "urn:li:jobPosting:1234567890")
                    if ":" in job_id:
                        job_id = job_id.split(":")[-1]
                    return job_id
            except:
                pass
            
            # Method 3: Try to find job ID in href of child link
            try:
                link = element.locator("a[href*='/jobs/view/']").first
                href = link.get_attribute("href", timeout=2000)
                if href and "/jobs/view/" in href:
                    # Extract ID from URL like: /jobs/view/1234567890/
                    parts = href.split("/jobs/view/")
                    if len(parts) > 1:
                        job_id = parts[1].split("/")[0].split("?")[0]
                        if job_id.isdigit():
                            return job_id
            except:
                pass
            
            # Method 4: Try data-entity-urn
            try:
                urn = element.get_attribute("data-entity-urn", timeout=2000)
                if urn and ":" in urn:
                    job_id = urn.split(":")[-1]
                    if job_id.isdigit():
                        return job_id
            except:
                pass
            
            logger.debug("Could not extract job ID from element", step="extract_job_id")
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract job ID: {e}", step="extract_job_id")
            return None

