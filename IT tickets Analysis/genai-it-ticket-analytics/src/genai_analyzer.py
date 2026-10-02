import os
import sys
import json
import time
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from utils import logger, ensure_dir
from prompts import build_ticket_analysis_prompt


class GenAIAnalyzer:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or config.GENAI_API_KEY
        self.model = model or config.GENAI_MODEL
        self.max_tickets = config.MAX_TICKETS_FOR_GENAI
        self.client = None
        self.use_mock = True
        self._init_client()

    def _init_client(self) -> None:
        if not self.api_key:
            logger.warning(
                "GENAI_API_KEY not provided. GenAI will run in MOCK mode. "
                "Set GENAI_API_KEY in .env to enable live LLM calls."
            )
            self.use_mock = True
            return
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
            self.use_mock = False
            logger.info(f"GenAI client initialized with model={self.model}")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client ({e}). Using mock mode.")
            self.use_mock = True

    def _parse_json_safe(self, text: str) -> dict:
        if not isinstance(text, str):
            return {}
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            candidate = text[start:end + 1]
            try:
                return json.loads(candidate)
            except Exception:
                pass
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("{") and s.endswith("}"):
                try:
                    return json.loads(s)
                except Exception:
                    continue
        return {}

    def _validate_genai_output(self, obj: dict) -> dict:
        required = ["summary", "category", "suggested_priority", "possible_cause", "suggested_resolution"]
        out = {}
        for k in required:
            v = obj.get(k, "Insufficient information")
            if v is None or not str(v).strip():
                v = "Insufficient information"
            out[k] = str(v).strip()
        valid_priorities = {"Low", "Medium", "High", "Critical"}
        if out["suggested_priority"] not in valid_priorities:
            out["suggested_priority"] = "Medium"
        valid_categories = {"Technical issue", "Billing inquiry", "Cancellation request",
                            "Refund request", "Product inquiry", "Other"}
        if out["category"] not in valid_categories:
            out["category"] = "Other"
        out["_genai_status"] = "ok"
        return out

    def _call_live(self, system: str, user: str, retries: int = 2, timeout: int = 30) -> str:
        import openai
        last_err = None
        for attempt in range(1, retries + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=0.2,
                    max_tokens=600,
                    timeout=timeout,
                )
                return resp.choices[0].message.content or ""
            except (openai.APITimeoutError, openai.RateLimitError, openai.APIConnectionError) as e:
                last_err = e
                wait = 2 ** attempt
                logger.warning(f"API error (attempt {attempt}): {e}. Waiting {wait}s...")
                time.sleep(wait)
            except Exception as e:
                last_err = e
                logger.warning(f"Unexpected API error (attempt {attempt}): {e}")
                break
        raise RuntimeError(f"Live GenAI call failed after retries: {last_err}")

    def _call_mock(self, ticket_type, ticket_subject, ticket_description, original_priority) -> dict:
        priority_map = {"Critical": "Critical", "High": "High", "Medium": "Medium", "Low": "Low"}
        sugg_pri = priority_map.get((original_priority or "").strip().title(), "Medium")
        cat = (ticket_type or "Other").strip()
        valid_categories = {"Technical issue", "Billing inquiry", "Cancellation request",
                            "Refund request", "Product inquiry"}
        if cat not in valid_categories:
            cat = "Other"
        subject = (ticket_subject or "issue").strip()
        product_ref = "the product"
        desc_lower = (ticket_description or "").lower()
        if "vpn" in desc_lower:
            cause = "Possible network connectivity or VPN authentication issue."
            steps = ("1. Verify internet connectivity.\n"
                     "2. Re-enter VPN credentials and retry connection.\n"
                     "3. Restart VPN client and device.\n"
                     "4. Escalate to Network Admin if issue persists.")
        elif "password" in desc_lower or "login" in desc_lower or "credential" in desc_lower or "access" in desc_lower:
            cause = "Possible invalid credentials or account lockout."
            steps = ("1. Verify username and password are correctly entered.\n"
                     "2. Use password reset flow if available.\n"
                     "3. Check account lockout / MFA status.\n"
                     "4. Contact IT access management if still blocked.")
        elif "billing" in desc_lower or "invoice" in desc_lower or "charge" in desc_lower or "payment" in desc_lower:
            cause = "Possible billing discrepancy or payment processing issue."
            steps = ("1. Review recent invoice details in the billing portal.\n"
                     "2. Verify payment method and available funds.\n"
                     "3. Confirm no duplicate authorization holds.\n"
                     "4. Escalate to billing team for adjustment if needed.")
        elif "update" in desc_lower or "software" in desc_lower or "firmware" in desc_lower or "install" in desc_lower:
            cause = "Possible software/firmware version incompatibility or interrupted update."
            steps = ("1. Confirm current version and target update version.\n"
                     "2. Restart device and retry update with stable network.\n"
                     "3. Roll back update if symptoms started immediately after.\n"
                     "4. Reinstall affected component if rollback does not help.")
        elif "battery" in desc_lower or "charge" in desc_lower or "power" in desc_lower or "turn on" in desc_lower:
            cause = "Possible battery degradation, faulty charger, or power supply issue."
            steps = ("1. Test with the original charger and cable.\n"
                     "2. Clean charging port and ensure connectors seat properly.\n"
                     "3. Allow continuous charge for 30 minutes and retry power on.\n"
                     "4. Escalate for hardware diagnostics if no response.")
        elif "network" in desc_lower or "wifi" in desc_lower or "internet" in desc_lower or "connect" in desc_lower:
            cause = "Possible local network disruption, Wi-Fi interference, or DNS issue."
            steps = ("1. Restart router and device network interfaces.\n"
                     "2. Confirm device is associated to the correct SSID.\n"
                     "3. Test with a wired connection or alternate hotspot.\n"
                     "4. Escalate to network team for further diagnostics.")
        else:
            cause = f"Possible issue related to '{subject}' requiring further triage."
            steps = (f"1. Reproduce the issue with {product_ref} and capture exact steps.\n"
                     "2. Review product manual / knowledge base for known fixes.\n"
                     "3. Apply any available software or firmware updates.\n"
                     "4. Escalate to the appropriate support team with logs.")
        summary = f"Ticket regarding {subject.lower()} under category {cat.lower()}. "
        if ticket_description and len(ticket_description) > 20:
            snippet = ticket_description.strip().replace("\n", " ")[:120]
            summary += f"User notes: {snippet}..."
        else:
            summary += "No additional detail provided in the ticket description."
        return {
            "summary": summary,
            "category": cat,
            "suggested_priority": sugg_pri,
            "possible_cause": cause,
            "suggested_resolution": steps,
            "_genai_status": "mock",
        }

    def analyze_ticket(self, row: pd.Series) -> dict:
        system, user = build_ticket_analysis_prompt(
            ticket_id=row.get("Ticket ID"),
            ticket_type=row.get("Ticket Type"),
            ticket_subject=row.get("Ticket Subject"),
            ticket_description=row.get("Ticket Description"),
            ticket_priority=row.get("Ticket Priority"),
            ticket_channel=row.get("Ticket Channel"),
            product_purchased=row.get("Product Purchased"),
        )
        if self.use_mock:
            raw = self._call_mock(
                ticket_type=row.get("Ticket Type"),
                ticket_subject=row.get("Ticket Subject"),
                ticket_description=row.get("Ticket Description"),
                original_priority=row.get("Ticket Priority"),
            )
            return self._validate_genai_output(raw)
        try:
            text = self._call_live(system, user)
            parsed = self._parse_json_safe(text)
            if not parsed:
                out = self._call_mock(
                    ticket_type=row.get("Ticket Type"),
                    ticket_subject=row.get("Ticket Subject"),
                    ticket_description=row.get("Ticket Description"),
                    original_priority=row.get("Ticket Priority"),
                )
                out["_genai_status"] = "json_parse_failed_fallback"
                return self._validate_genai_output(out)
            return self._validate_genai_output(parsed)
        except Exception as e:
            logger.warning(f"Live GenAI failed for ticket {row.get('Ticket ID')}: {e}. Using mock.")
            out = self._call_mock(
                ticket_type=row.get("Ticket Type"),
                ticket_subject=row.get("Ticket Subject"),
                ticket_description=row.get("Ticket Description"),
                original_priority=row.get("Ticket Priority"),
            )
            out["_genai_status"] = f"api_error_fallback: {e}"
            return self._validate_genai_output(out)

    def analyze_dataframe(self, df: pd.DataFrame, max_tickets: int = None) -> pd.DataFrame:
        if max_tickets is None:
            max_tickets = self.max_tickets
        total = len(df)
        n = min(total, max_tickets if max_tickets and max_tickets > 0 else total)
        logger.info(f"GenAI analysis requested for {n}/{total} tickets (live={not self.use_mock})")
        sample = df.head(n).copy().reset_index(drop=True)
        results = []
        for i, (_, row) in enumerate(sample.iterrows(), start=1):
            if i % 10 == 0 or i == 1 or i == n:
                logger.info(f"  Processing ticket {i}/{n}")
            r = self.analyze_ticket(row)
            r["ticket_id"] = row.get("Ticket ID")
            results.append(r)
        result_df = pd.DataFrame(results)
        ensure_dir(config.GENAI_RESULTS_DIR)
        result_df.to_csv(config.GENAI_OUTPUT_FILE, index=False)
        logger.info(f"GenAI output saved to {config.GENAI_OUTPUT_FILE} ({len(result_df)} rows)")
        return result_df


def run_genai_pipeline(df: pd.DataFrame) -> tuple[pd.DataFrame, GenAIAnalyzer]:
    analyzer = GenAIAnalyzer()
    result_df = analyzer.analyze_dataframe(df)
    mode = "MOCK" if analyzer.use_mock else f"LIVE ({analyzer.model})"
    n = len(result_df)
    summary_text = (
        f"GenAI analysis was performed on {n} tickets using {mode} mode.\n"
        f"Output saved to: {config.GENAI_OUTPUT_FILE}\n"
    )
    logger.info(summary_text.strip())
    return result_df, analyzer
