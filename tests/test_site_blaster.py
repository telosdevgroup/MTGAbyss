import pytest
from scripts.site_blaster import SiteBlaster
from scripts.blast_all import run_blasters

@pytest.fixture(scope="module")
def blaster():
    return SiteBlaster(seed=42)

def test_siteblaster_network_subdomain_routing(blaster):
    blaster.test_network_subdomain_routing()
    assert blaster.failed == 0, f"Failures in subdomain routing: {blaster.failures_recap}"

def test_siteblaster_contact_and_honeypot(blaster):
    blaster.test_contact_and_honeypot()
    assert blaster.failed == 0, f"Failures in contact/honeypot: {blaster.failures_recap}"

def test_siteblaster_auth_and_sso_surfaces(blaster):
    blaster.test_auth_surfaces()
    assert blaster.failed == 0, f"Failures in auth surfaces: {blaster.failures_recap}"

def test_blast_all_registry():
    from scripts.blast_all import SiteBlaster, DominionSiteBlaster, SWUSiteBlaster, NecromundaSiteBlaster
    # Verify all 4 game blasters are imported and registered
    assert SiteBlaster is not None
    assert DominionSiteBlaster is not None
    assert SWUSiteBlaster is not None
    assert NecromundaSiteBlaster is not None
