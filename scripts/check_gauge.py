"""Verifica la aguja integrada en el manómetro CAD, sin panel separado."""
import math
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8001'
shots = Path(__file__).resolve().parents[1] / 'documentacion' / 'capturas'
shots.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1100}, reduced_motion='reduce')
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(url + '/?pieza=74')
    page.wait_for_selector('#viewport[data-ready="true"]')
    assert page.locator('#gauge-panel').count() == 0, 'No debe existir un instrumento separado del CAD'
    view = page.locator('#viewport')
    view.scroll_into_view_if_needed()
    assert view.get_attribute('data-selected-part') == '74'
    assert view.get_attribute('data-gauge74-needle-visible') == 'false'
    off = view.screenshot(path=str(shots / 'manometro-3d-apagado.png'))

    def input_value(selector, value):
        page.locator(selector).evaluate('(node, value) => { node.value = value; node.dispatchEvent(new Event("input", { bubbles: true })); }', value)

    def check_angle():
        piece = view.get_attribute('data-selected-part')
        pressure = float(view.get_attribute(f'data-gauge{piece}-pressure-bar'))
        target = -135 + 270 * pressure / 70
        page.wait_for_function('(args) => Math.abs(Number(document.getElementById("viewport").getAttribute(`data-gauge${args[0]}-needle-angle`)) - args[1]) < .001', arg=[piece, target])
        return target

    page.locator('#pump-toggle').evaluate('(node) => node.click()')
    assert view.get_attribute('data-gauge74-needle-visible') == 'false', 'Presión desconocida con alimentación cerrada'
    input_value('#valve-opening', 100)
    first = check_angle()
    assert view.get_attribute('data-gauge74-needle-visible') == 'true'
    operating = view.screenshot(path=str(shots / 'manometro-3d-desktop.png'))
    assert off != operating, 'La aguja debe cambiar la imagen renderizada del objeto 3D'
    page.locator('#piece').select_option('71')
    view.scroll_into_view_if_needed()
    assert view.get_attribute('data-selected-part') == '72'
    assert 'Manómetro analógico' in page.locator('#piece option[value="71"]').inner_text()
    check_angle()
    view.screenshot(path=str(shots / 'manometro-72-3d.png'))
    assert '72:' in page.locator('#gauge-status').inner_text() and '74:' in page.locator('#gauge-status').inner_text()
    page.emulate_media(reduced_motion='no-preference')
    input_value('#pump-frequency', 35)
    assert check_angle() < first
    input_value('#pump-frequency', 45)
    input_value('#pump-frequency', 50)
    check_angle()
    # Move the instrument numerically, then disconnect a real pipe in the circuit.
    page.locator('#piece-x').fill('.1')
    page.locator('#piece-x').press('Tab')
    page.locator('#reset-piece').click()
    page.locator('#piece').select_option('123')
    page.locator('#piece-x').fill('.1')
    page.locator('#piece-x').press('Tab')
    assert view.get_attribute('data-gauge74-needle-visible') == 'false', 'Circuito desconectado: sin presión estimada'
    page.locator('#reset-piece').click()
    page.locator('#piece').select_option('73')
    view.scroll_into_view_if_needed()
    check_angle()
    page.locator('#piece').select_option('182')
    assert page.locator('#pump-info').is_visible()
    page.locator('#piece').select_option('73')
    page.emulate_media(reduced_motion='reduce')
    page.set_viewport_size({'width': 390, 'height': 844})
    view.scroll_into_view_if_needed()
    check_angle()
    view.screenshot(path=str(shots / 'manometro-3d-mobile.png'))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    browser.close()

print('OK: manómetro en CAD, selección frontal, aguja renderizada, controles, interrupción, desconexión, movimiento reducido y móvil.')
