import os
import sys
sys.path.insert(0, '.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'E_learning.settings'
import django
django.setup()

from django.test.runner import DiscoverRunner
import unittest

runner = DiscoverRunner(verbosity=1, interactive=False, fail_fast=False)

loader = unittest.TestLoader()
suite = unittest.TestSuite()

for module_name in ['accounts.test_api', 'accounts.tests', 'courses.test_api', 'courses.tests', 'payments.test_api', 'payments.tests']:
    try:
        tests = loader.loadTestsFromName(module_name)
        suite.addTests(tests)
        print(f'Loaded {module_name}: {suite.countTestCases()} tests')
    except Exception as e:
        print(f'Could not load {module_name}: {e}')

result = runner.run_suite(suite)
print('--- Summary ---')
print('Ran:', result.testsRun)
print('Failures:', len(result.failures))
print('Errors:', len(result.errors))

