from nose import SkipTest

from yolk.yolklib import get_highest_version

class TestDistributions:
    def test_object_initialization(self):
        raise SkipTest # TODO: implement your test here

    def test_query_activated(self):
        raise SkipTest # TODO: implement your test here

    def test_get_distributions(self):
        raise SkipTest # TODO: implement your test here

    def test_get_alpha(self):
        raise SkipTest # TODO: implement your test here

    def test_get_packages(self):
        raise SkipTest # TODO: implement your test here

    def test_case_sensitive_name(self):
        raise SkipTest # TODO: implement your test here

    def test_get_highest_installed(self):
        raise SkipTest # TODO: implement your test here

class TestGetHighestVersion:

    def test_get_highest_version(self):
        assert get_highest_version(['1.0', '2.0']) == '2.0' 
        assert get_highest_version(['2.0', '2.0']) == '2.0' 
