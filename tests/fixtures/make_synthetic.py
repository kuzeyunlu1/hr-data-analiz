"""Build a SYNTHETIC Google Forms export for tests.

Uses the real header row (tests/fixtures/header.csv — question texts only, no respondent data) and
fabricated answers. Each profile exercises specific pipeline behaviour; see PROFILES below.
Never copy real responses into this file.

Usage: python tests/fixtures/make_synthetic.py <out.csv>
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent
HEADER_PATH = FIXTURES / "header.csv"

FACTORS = (
    "pay",
    "recognition",
    "job_security",
    "rel_colleagues",
    "rel_supervisor",
    "workload",
    "work_life_balance",
    "autonomy",
    "development",
    "interesting_tasks",
    "meaningful_work",
    "info_access",
    "idea_contribution",
    "tools_resources",
)
Q18_ITEMS = (
    "q18a_disagreement_constructive",
    "q18b_effort_appreciated",
    "q18c_recognition_timely",
    "q18d_recognition_fair",
    "q18e_reward_criteria_clear",
    "q18f_supported_by_leadership",
    "q18g_priorities_clear",
    "q18h_time_sufficient",
    "q18i_voice_safety",
    "q18j_recommend_employer",
)
IMP = {
    3: "Moderately important / Mittelmäßig wichtig",
    4: "Very important / Sehr wichtig",
    5: "Extremely important / Äußerst wichtig",
}
SAT = {
    1: "Very dissatisfied / Sehr unzufrieden",
    2: "Dissatisfied / Unzufrieden",
    3: "Neither satisfied nor dissatisfied / Weder zufrieden noch unzufrieden",
    4: "Satisfied / Zufrieden",
    5: "Very satisfied / Sehr zufrieden",
}
QUALITY_NA = "Not enough experience to judge / Nicht genügend Erfahrung, um dies zu beurteilen"
AGREE = {
    1: "Strongly disagree / Stimme überhaupt nicht zu",
    3: "Neither agree nor disagree / Stimme weder zu noch nicht zu",
    4: "Agree / Stimme zu",
    5: "Strongly agree / Stimme voll und ganz zu",
}
AGREE_NA = "Unable to judge / Kann ich nicht beurteilen"
PROB = {
    2: "25% — Unlikely / Unwahrscheinlich",
    3: "50% — Equally likely and unlikely / Ebenso wahrscheinlich wie unwahrscheinlich",
    4: "75% — Likely / Wahrscheinlich",
}
DESIRE_NEUTRAL = "Neither desirable nor undesirable / Weder erwünscht noch unerwünscht"
DESIRE_HIGH = "Very desirable / Sehr erwünscht"


def _grids(imp: list[int], sat: list[int], q18: list[int]) -> dict[str, str]:
    cells = {f"q16_imp_{f}": IMP[c] for f, c in zip(FACTORS, imp, strict=True)}
    cells |= {f"q17_sat_{f}": SAT[c] for f, c in zip(FACTORS, sat, strict=True)}
    cells |= {item: str(c) for item, c in zip(Q18_ITEMS, q18, strict=True)}
    return cells


def _tech_positive() -> dict[str, str]:
    return {
        "submitted_at_raw": "2026/10/14 12:05:00 ÖÖ GMT+3",
        "q01_customer_value_txt": "Fast response times when systems fail.",
        "q02_customer_problem_txt": "Customers ask for monthly security reports.",
        "q03_business_opportunity_txt": "Offer a security review; first step: list ten candidates.",
        "q04_coop_within_dept": "Very good / Sehr gut",
        "q04_1_coop_within_reason_txt": "Colleagues always help each other.",
        "q05_coop_cross_dept": "Good / Gut",
        "q05_1_coop_cross_reason_txt": "Most teams respond quickly.\nSome details get lost.",
        "q06_coop_change_txt": "A weekly 15-minute sync between delivery and sales.",
        "q07_info_access_sat": SAT[5],
        "q08_info_access_change_txt": "No change is necessary.",
        "q09_role_clarity_own": "Very clear / Sehr klar",
        "q10_role_clarity_others": "Clear / Klar",
        "q10_1_role_unclear_txt": "The responsibilities are clear.",
        "q11_reachability": "Very easy / Sehr einfach",
        "q12_obstacles_txt": "There is no obstacle.",
        "q13a_info_clear": AGREE[5],
        "q13b_change_informed_timely": AGREE[4],
        "q14_pride_txt": "Our technical expertise.",
        "q15_enjoy_txt": "Solving hard problems as a team.",
        **_grids(
            [5, 4, 4, 4, 4, 4, 5, 5, 5, 5, 4, 4, 4, 4],
            [4, 5, 4, 5, 5, 4, 5, 5, 4, 5, 4, 4, 5, 4],
            [4, 4, 4, 5, 4, 5, 5, 4, 5, 5],
        ),
        "q18_1_top_motivator_txt": "Professional development, technology changes quickly.",
        "q19_expectancy": PROB[4],
        "q20_instrumentality": PROB[4],
        "q21_valence": DESIRE_HIGH,
        "q22_motivation_2w": "8",
        "q23_company_support": "4",
        "q24_top_suggestion_txt": "A shared ticket view for sales and delivery.",
        "tec1_customer_requests_txt": "Security assessments.",
        # tec2 deliberately blank: an unanswered item in the OWN branch is EMPTY, not NOT_ROUTED
        "tec4_handover_completeness": "Very complete / Sehr vollständig",
        "tec5_handover_missing_info_txt": "I'm not in a position to answer that",
        "tec6_avoidable_work_txt": "Documenting undocumented customer networks.",
        "tec7_single_change_txt": "A standard onboarding checklist.",
    }


def _sales_negative() -> dict[str, str]:
    return {
        "submitted_at_raw": "2026/10/14 12:30:00 ÖS GMT+3",
        "q01_customer_value_txt": (
            "Ehrliche Beratung – Kunden schätzen, dass wir nur verkaufen, was sie brauchen."
        ),
        "q03_business_opportunity_txt": "Nothing is achievable in 30 days.",
        "q04_coop_within_dept": QUALITY_NA,
        "q04_1_coop_within_reason_txt": "I work alone in my function.",
        "q05_coop_cross_dept": "Neither poor nor good / Weder schlecht noch gut",
        "q05_1_coop_cross_reason_txt": "It depends on the department.",
        "q06_coop_change_txt": "-",
        "q07_info_access_sat": SAT[2],
        "q08_info_access_change_txt": "A shared wiki for product information.",
        "q09_role_clarity_own": "Very unclear / Sehr unklar",
        "q10_role_clarity_others": "Clear / Klar",
        "q10_1_role_unclear_txt": "My own responsibilities change every few months.",
        "q11_reachability": "Easy / Einfach",
        "q12_obstacles_txt": "Priorities change constantly.",
        "q13a_info_clear": AGREE_NA,
        "q13b_change_informed_timely": AGREE[1],
        "q14_pride_txt": "I dont know?",
        "q15_enjoy_txt": "Weiß ich nicht",
        **_grids(
            [4, 3, 5, 4, 4, 4, 5, 5, 3, 5, 5, 3, 4, 5],
            [2, 3, 1, 4, 3, 2, 1, 2, 3, 4, 1, 3, 4, 3],
            [2, 2, 1, 4, 1, 1, 5, 3, 4, 1],
        ),
        "q18_1_top_motivator_txt": "Work-life balance.",
        "q19_expectancy": PROB[2],
        "q20_instrumentality": PROB[3],
        "q21_valence": DESIRE_NEUTRAL,
        "q22_motivation_2w": "0",
        "q23_company_support": "2",
        "q24_top_suggestion_txt": "Make decisions faster.",
        "sal1_growth_segment_txt": "Mid-sized manufacturers.",
        "sal2_high_value_service_txt": "Infrastructure analysis.",
        "sal3_internal_hindrance": "Moderately / Mäßig",
        "sal4_main_obstacle_txt": "No capacity for new processes.",
        "sal5_value_convince_difficulty": "Not difficult at all / Überhaupt nicht schwierig",
        "sal6_difficulty_reason_txt": "High closing rate once we present.",
        "sal7_single_change_txt": "I couldn't think of one",
    }


def _backoffice_mixed() -> dict[str, str]:
    return {
        "submitted_at_raw": "2026/10/15 9:15:42 ÖS GMT+3",
        "q01_customer_value_txt": "Reliable order processing.",
        "q04_coop_within_dept": "Good / Gut",
        "q05_coop_cross_dept": "Good / Gut",
        "q07_info_access_sat": SAT[3],
        "q09_role_clarity_own": "Clear / Klar",
        "q10_role_clarity_others": "Very clear / Sehr klar",
        "q11_reachability": "Easy / Einfach",
        "q12_obstacles_txt": "No obstacle, but the VPN drops daily.",
        "q13a_info_clear": AGREE[3],
        "q13b_change_informed_timely": AGREE[4],
        **_grids(
            [4, 4, 4, 4, 4, 5, 5, 4, 4, 4, 4, 5, 4, 4],
            [3, 3, 4, 4, 4, 3, 4, 4, 3, 3, 4, 3, 3, 3],
            [3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
        ),
        "q19_expectancy": PROB[3],
        "q20_instrumentality": PROB[4],
        "q21_valence": DESIRE_NEUTRAL,
        "q22_motivation_2w": "5",
        "q23_company_support": "3",
        "bo1_delay_step_txt": "Waiting for missing order details.",
        "bo2_info_completeness": "Complete / Vollständig",  # expected (unverified) label
        "bo3_missing_info_txt": "Delivery address and VAT ID.",
        "bo4_handover_eff": "Very effectively / Sehr effektiv",
        "bo5_handover_improve_txt": "One intake form for all orders.",
        "bo6_recurring_enquiries_txt": "Customers ask for order status updates.",
        "bo7_single_change_txt": "Fewer manual copy-paste steps.",
    }


def _none_inconsistent() -> dict[str, str]:
    return {
        "submitted_at_raw": "2026/10/15 1:00:00 ÖÖ GMT+3",
        "q01_customer_value_txt": "I don´t have any direct customer contact.",
        "q03_business_opportunity_txt": "Timely and regular communication.",
        "q04_coop_within_dept": "Good / Gut",
        "q05_coop_cross_dept": "Good / Gut",
        "q07_info_access_sat": SAT[4],
        "q08_info_access_change_txt": (
            "No change is necessary. If I need access to information, I'll find a way to get it"
        ),
        "q09_role_clarity_own": "Very clear / Sehr klar",
        "q10_role_clarity_others": "Clear / Klar",
        "q10_1_role_unclear_txt": "The responsibilities are clear.",
        "q11_reachability": "Very easy / Sehr einfach",
        "q12_obstacles_txt": (
            "No obstacle in my team, but other departments never answer my emails "
            "and I lose hours every week."
        ),
        "q13a_info_clear": AGREE[4],
        "q13b_change_informed_timely": AGREE[4],
        **_grids(
            [4, 5, 4, 3, 4, 4, 4, 5, 5, 5, 4, 4, 5, 4],
            [4, 4, 4, 5, 5, 4, 4, 5, 4, 4, 5, 4, 5, 4],
            [5, 5, 5, 5, 5, 5, 5, 5, 5, 1],
        ),
        "q19_expectancy": PROB[4],
        "q20_instrumentality": PROB[4],
        "q21_valence": DESIRE_NEUTRAL,
        "q22_motivation_2w": "8",
        "q23_company_support": "4",
    }


def _straightliner() -> dict[str, str]:
    return {
        "submitted_at_raw": "2026/10/15 3:20:00 ÖS GMT+3",
        "q01_customer_value_txt": ".",
        "q04_coop_within_dept": "Very good / Sehr gut",
        "q05_coop_cross_dept": "Very good / Sehr gut",
        "q06_coop_change_txt": "n/a",
        "q07_info_access_sat": SAT[5],
        "q09_role_clarity_own": "Very clear / Sehr klar",
        "q10_role_clarity_others": "Very clear / Sehr klar",
        "q11_reachability": "Very easy / Sehr einfach",
        "q12_obstacles_txt": "-",
        "q13a_info_clear": AGREE[5],
        "q13b_change_informed_timely": AGREE[5],
        **_grids([5] * 14, [5] * 14, [4, 4, 4, 4, 4, 4, 4, 4, 4, 5]),
        "q19_expectancy": PROB[4],
        "q20_instrumentality": PROB[4],
        "q21_valence": DESIRE_HIGH,
        "q22_motivation_2w": "10",
        "q23_company_support": "5",
    }


def _low_completion() -> dict[str, str]:
    return {
        "submitted_at_raw": "2026/10/15 11:59:59 ÖS GMT+3",
        "q01_customer_value_txt": "Good service.",
        "q04_coop_within_dept": "Good / Gut",
        "q05_coop_cross_dept": "Good / Gut",
    }


def _multi_branch() -> dict[str, str]:
    """Answers in two branch blocks — the form routing should make this impossible."""
    core = {k: v for k, v in _tech_positive().items() if not k.startswith(("tec", "sal", "bo"))}
    return {
        **core,
        "submitted_at_raw": "2026/10/15 4:44:44 ÖS GMT+3",
        "q22_motivation_2w": "7",
        "tec1_customer_requests_txt": "Backup monitoring.",
        "tec2_needs_to_sales_eff": "Very effectively / Sehr effektiv",
        "sal1_growth_segment_txt": "Existing customers without a support contract.",
        "sal3_internal_hindrance": "Moderately / Mäßig",
    }


def _duplicate_of_inconsistent() -> dict[str, str]:
    return {**_none_inconsistent(), "submitted_at_raw": "2026/10/16 10:00:00 ÖÖ GMT+3"}


# name -> builder; dict order = row order in the synthetic export (tests rely on it)
PROFILES = {
    "tech_positive": _tech_positive,
    "sales_negative": _sales_negative,
    "backoffice_mixed": _backoffice_mixed,
    "none_inconsistent": _none_inconsistent,
    "straightliner": _straightliner,
    "low_completion": _low_completion,
    "duplicate": _duplicate_of_inconsistent,
    "multi_branch": _multi_branch,
}


def read_header(path: Path = HEADER_PATH) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return next(csv.reader(handle))


def build_rows(var_ids: list[str]) -> list[list[str]]:
    rows = []
    for builder in PROFILES.values():
        cells = builder()
        unknown = set(cells) - set(var_ids)
        if unknown:
            raise KeyError(f"synthetic profile uses unknown var_ids: {sorted(unknown)}")
        rows.append([cells.get(var_id, "") for var_id in var_ids])
    return rows


def write_synthetic(var_ids: list[str], out_path: Path) -> Path:
    header = read_header()
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(build_rows(var_ids))
    return out_path


if __name__ == "__main__":
    from hrsurvey.config import load_config

    config = load_config(Path(__file__).resolve().parents[2] / "config")
    target = write_synthetic([c.var_id for c in config.survey.columns], Path(sys.argv[1]))
    print(f"wrote {target}")
