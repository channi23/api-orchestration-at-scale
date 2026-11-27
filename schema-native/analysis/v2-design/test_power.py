"""Hermetic checks for planning mistakes that would inflate independent n."""
import copy
import unittest

from power import final_select, observed_cluster_power, paired_audit, paired_n


def row(arm, intent, index, correct, prefix=None):
    unit = f"select|UNIT|C{index}|{intent}"
    return {"arm": arm, "family": "select", "unit_key": unit,
            "request_key": (prefix or arm) + "|" + unit,
            "intent_id": intent, "eval": {"e2e_success": correct}}


class PlanningTests(unittest.TestCase):
    def test_controls_and_retry_records_are_not_extra_final_units(self):
        rows = [row("F0", "i", 0, True), row("F0", "i", 0, False, "determinism"),
                row("F0", "i", 0, False, "retry")]
        self.assertEqual(len(final_select(rows, "F0")), 1)

    def test_duplicate_final_is_an_error(self):
        r = row("A", "i", 0, True)
        with self.assertRaises(ValueError):
            final_select([r, r], "A")

    def test_unmatched_pairs_are_an_error(self):
        with self.assertRaises(ValueError):
            paired_audit([row("A", "i", 0, True), row("B", "j", 0, True)], "A", "B")

    def test_cluster_means_and_discordance_preserve_repetitions(self):
        rows = [row(arm, intent, i, arm == "B" and intent == "one")
                for arm in ("A", "B") for intent in ("one", "two") for i in range(4)]
        original = copy.deepcopy(rows)
        audit, means = paired_audit(rows, "A", "B")
        self.assertEqual((audit["final_select_pairs"], audit["independent_intents"]), (8, 2))
        self.assertEqual(means, [1, 0])
        self.assertEqual(audit["b_only_correct"], 4)
        self.assertEqual(audit["difference_pp"], 50)
        self.assertEqual(audit["descriptive_design_effect"], 7)
        self.assertEqual(rows, original)

    def test_unbalanced_clusters_not_silently_reweighted(self):
        rows = [row(arm, "one", 0, True) for arm in ("A", "B")]
        rows += [row(arm, "two", i, True) for arm in ("A", "B") for i in range(2)]
        with self.assertRaises(ValueError):
            paired_audit(rows, "A", "B")

    def test_normal_approximation_matches_independent_calculation(self):
        # z_.975=1.9599639845 and z_.8=.8416212336 give n=626 at q=.20, delta=.05.
        self.assertEqual(paired_n(.05, .2), 626)
        self.assertEqual(paired_n(.05, .2, alpha=.025), 758)
        self.assertGreater(paired_n(.03, .2), paired_n(.05, .2))
        self.assertGreater(paired_n(.05, .3), paired_n(.05, .2))

    def test_invalid_planning_assumptions_rejected(self):
        for delta, q in [(0, .2), (.3, .2), (.05, 1.1)]:
            with self.assertRaises(ValueError):
                paired_n(delta, q)

    def test_cluster_simulation_is_seeded_and_counts_no_signal_as_no_power(self):
        first = observed_cluster_power([0, .25, 1], 10, .05, repeats=50)
        self.assertEqual(first, observed_cluster_power([0, .25, 1], 10, .05, repeats=50))
        self.assertEqual(observed_cluster_power([0, 0], 10, .05, repeats=50)["conditional_power"], 0)


if __name__ == "__main__":
    unittest.main()
