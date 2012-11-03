import unittest

import yolk.yolklib



class TestStdOut:
    def test_object_initialization(self):
        pass # TODO: implement your test here

    def test_write(self):
        pass # TODO: implement your test here

    def test_writelines(self):
        pass # TODO: implement your test here

class TestYolk:
    def test_object_initialization(self):
        pass # TODO: implement your test here

    def test_get_plugin(self):
        pass # TODO: implement your test here

    def test_set_log_level(self):
        pass # TODO: implement your test here

    def test_run(self):
        pass # TODO: implement your test here

    def test_show_active(self):
        pass # TODO: implement your test here

    def test_show_non_active(self):
        pass # TODO: implement your test here

    def test_show_all(self):
        pass # TODO: implement your test here

    def test_show_updates(self):
        pass # TODO: implement your test here

    def test_show_distributions(self):
        pass # TODO: implement your test here

    def test_print_metadata(self):
        pass # TODO: implement your test here

    def test_show_deps(self):
        pass # TODO: implement your test here

    def test_show_pypi_changelog(self):
        pass # TODO: implement your test here

    def test_show_pypi_releases(self):
        pass # TODO: implement your test here

    def test_show_download_links(self):
        pass # TODO: implement your test here

    def test_print_download_uri(self):
        pass # TODO: implement your test here

    def test_fetch(self):
        pass # TODO: implement your test here

    def test_fetch_uri(self):
        pass # TODO: implement your test here

    def test_fetch_svn(self):
        pass # TODO: implement your test here

    def test_browse_website(self):
        pass # TODO: implement your test here

    def test_query_metadata_pypi(self):
        pass # TODO: implement your test here

    def test_versions_available(self):
        pass # TODO: implement your test here

    def test_parse_search_spec(self):
        pass # TODO: implement your test here

    def test_pypi_search(self):
        pass # TODO: implement your test here

    def test_show_entry_map(self):
        pass # TODO: implement your test here

    def test_show_entry_points(self):
        pass # TODO: implement your test here

    def test_yolk_version(self):
        pass # TODO: implement your test here

    def test_parse_pkg_ver(self):
        pass # TODO: implement your test here

class TestSetupOptParser:
    def test_setup_opt_parser(self):
        pass # TODO: implement your test here

class TestPrintPkgVersions:
    def test_print_pkg_versions(self):
        pass # TODO: implement your test here

class TestValidatePypiOpts:
    def test_validate_pypi_opts(self):
        pass # TODO: implement your test here

class TestMain:
    def test_main(self):
        pass # TODO: implement your test here
 
 
class TestYolkLib (unittest.TestCase):
    def test_get_highest_version(self):
        versions = ['2.2', '3.0.5', '1.3', '3.1.2', '1.3.4', '0.3', '3.1.1', '1.2.4']
        self.assertEqual('3.1.2', yolk.yolklib.get_highest_version(versions))
