import json
import unittest

from contracts import ContractError, validate_ticket


class ContractTests(unittest.TestCase):
    def sample(self, **overrides):
        record = {"category": "hardware", "priority": "normal", "reason": "Fan noise"}
        record.update(overrides)
        return json.dumps(record)

    def test_valid(self):
        self.assertEqual(validate_ticket(self.sample())["priority"], "normal")

    def test_not_an_object(self):
        with self.assertRaises(ContractError):
            validate_ticket('[]')

    def test_not_json(self):
        with self.assertRaises(ContractError):
            validate_ticket('{broken')

    def test_extra_field(self):
        with self.assertRaises(ContractError):
            validate_ticket(self.sample(execute_command="id"))

    def test_missing_field(self):
        with self.assertRaises(ContractError):
            validate_ticket('{"category":"other","priority":"low"}')

    def test_invalid_category(self):
        with self.assertRaises(ContractError):
            validate_ticket(self.sample(category="root"))

    def test_invalid_priority(self):
        with self.assertRaises(ContractError):
            validate_ticket(self.sample(priority="emergency"))

    def test_reason_must_be_string(self):
        with self.assertRaises(ContractError):
            validate_ticket(self.sample(reason=["not", "string"]))

    def test_reason_length_limit(self):
        with self.assertRaises(ContractError):
            validate_ticket(self.sample(reason="x" * 241))

    def test_empty_reason(self):
        with self.assertRaises(ContractError):
            validate_ticket(self.sample(reason=""))

    def test_response_byte_limit(self):
        with self.assertRaises(ContractError):
            validate_ticket(" " * 4097)

    def test_non_string(self):
        with self.assertRaises(ContractError):
            validate_ticket(None)


if __name__ == "__main__":
    unittest.main()
