"""Comprueba que las variables de la bomba gobiernan el agua y las lecturas."""
from pathlib import Path
from playwright.sync_api import sync_playwright

SHOTS = Path(__file__).resolve().parents[1] / 'documentacion' / 'capturas'


def slider(page, name, value):
    page.locator('#' + name).evaluate('(node, value) => { node.value=value; node.dispatchEvent(new Event("input", {bubbles:true})); }', str(value))


with sync_playwright() as p:
    browser = p.chromium.launch(args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':1440, 'height':1100}, reduced_motion='reduce')
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8001')
    page.wait_for_selector('#viewport[data-ready="true"]')
    assert page.locator('#viewport').get_attribute('data-pump-state') == 'off'
    page.locator('#valve-opening').evaluate('(node) => { node.value = Number(node.value) > 0 ? 0 : 100; node.dispatchEvent(new Event("input", {bubbles:true})); }')
    assert page.locator('#viewport').get_attribute('data-water-open') == 'false'
    page.locator('#pump-toggle').click()
    assert page.locator('#viewport').get_attribute('data-pump-state') == 'operating'
    assert page.locator('#viewport').get_attribute('data-water-open') == 'true'
    nominal = float(page.locator('#viewport').get_attribute('data-pump-flow-l-min'))
    assert 25 < nominal < 30
    assert float(page.locator('#viewport').get_attribute('data-pump-pressure-bar')) > 10
    page.screenshot(path=str(SHOTS / 'bomba-desktop.png'), full_page=True)
    slider(page, 'pump-frequency', 25)
    lower = float(page.locator('#viewport').get_attribute('data-pump-flow-l-min'))
    assert 0 < lower < nominal
    assert abs(float(page.locator('#viewport').get_attribute('data-pump-shaft-reference-kw')) - .1375) < 1e-8
    slider(page, 'pump-frequency', 50)
    slider(page, 'valve-opening', 50)
    assert float(page.locator('#viewport').get_attribute('data-pump-flow-l-min')) < nominal
    slider(page, 'valve-opening', 0)
    assert page.locator('#viewport').get_attribute('data-water-open') == 'false'
    assert page.locator('#viewport').get_attribute('data-pump-pressure-bar') == ''
    slider(page, 'valve-opening', 100)
    slider(page, 'pump-frequency', 0)
    assert page.locator('#viewport').get_attribute('data-pump-flow-l-min') == '0'
    slider(page, 'pump-frequency', 50)
    slider(page, 'valve-opening', 1)
    assert page.locator('#viewport').get_attribute('data-pump-state') == 'outside_curve'
    assert page.locator('#viewport').get_attribute('data-pump-flow-l-min') == ''
    slider(page, 'valve-opening', 100)
    page.locator('summary').click()
    page.locator('#static-head').fill('200')
    page.locator('#static-head').press('Tab')
    assert page.locator('#viewport').get_attribute('data-pump-state') == 'outside_curve'
    page.locator('#static-head').fill('1')
    page.locator('#static-head').press('Tab')
    page.locator('#circuit-loss').fill('-1')
    page.locator('#circuit-loss').press('Tab')
    assert page.locator('#viewport').get_attribute('data-pump-state') == 'invalid'
    page.locator('#circuit-loss').fill('40')
    page.locator('#circuit-loss').press('Tab')
    page.locator('summary').click()
    # Moving the pump body must block the estimated flow, not keep pumping through a gap.
    page.locator('#piece').select_option('182')
    page.locator('#piece-x').fill('.1')
    page.locator('#piece-x').press('Tab')
    assert page.locator('#viewport').get_attribute('data-pump-state') == 'disconnected'
    assert page.locator('#viewport').get_attribute('data-water-open') == 'false'
    page.locator('#reset-pieces').click()
    assert page.locator('#viewport').get_attribute('data-pump-state') == 'operating'
    page.emulate_media(reduced_motion='no-preference')
    page.locator('#viewport').scroll_into_view_if_needed()
    first = float(page.locator('#viewport').get_attribute('data-water-travelled-m'))
    page.wait_for_timeout(300)
    full_distance = float(page.locator('#viewport').get_attribute('data-water-travelled-m')) - first
    slider(page, 'pump-frequency', 25)
    first = float(page.locator('#viewport').get_attribute('data-water-travelled-m'))
    page.wait_for_timeout(300)
    half_distance = float(page.locator('#viewport').get_attribute('data-water-travelled-m')) - first
    assert 0 < half_distance < full_distance, 'El avance visible debe responder al caudal calculado'
    page.locator('#pump-toggle').click()
    assert page.locator('#viewport').get_attribute('data-water-open') == 'false'
    page.set_viewport_size({'width':390, 'height':844})
    page.screenshot(path=str(SHOTS / 'bomba-mobile.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    browser.close()
print('OK: bomba, frecuencia, llave, caudal/presion/potencias, limites de curva, desconexion, agua variable y movil.')
