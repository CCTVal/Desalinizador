"""Ficha discreta al pasar el mouse; selección, toque y estado actualizado."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':1440, 'height':1100}, reduced_motion='reduce')
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8001')
    page.wait_for_selector('#viewport[data-ready="true"]')
    info = page.locator('#pump-info')
    assert not info.is_visible()
    page.locator('#piece').select_option('182')
    assert info.is_visible()
    for value in ['WDM VSSE 1-23', 'Acero inoxidable 304', '32 mm', '1,1 kW', '1,5 HP', '380 V', '50 Hz']:
        assert value in info.inner_text(), value
    assert 'Bomba apagada' in page.locator('#pump-info-status').inner_text()
    page.locator('#pump-toggle').click()
    page.locator('#valve-opening').evaluate('(node) => { node.value = Number(node.value) > 0 ? 0 : 100; node.dispatchEvent(new Event("input", {bubbles:true})); }')
    assert 'Punto de trabajo estimado' in page.locator('#pump-info-status').inner_text()
    view = page.locator('#viewport')
    view.scroll_into_view_if_needed()
    rect = view.bounding_box()
    page.mouse.move(rect['x'] + 8, rect['y'] + 8)
    page.wait_for_function('document.getElementById("pump-info").hidden')
    assert not info.is_visible()
    selected = view.get_attribute('data-selected-part')
    page.mouse.move(rect['x'] + rect['width'] * .52, rect['y'] + rect['height'] * .65)
    page.wait_for_selector('#pump-info:visible')
    assert view.get_attribute('data-selected-part') == selected, 'Hover no cambia la selección'
    assert info.bounding_box()['width'] <= 264
    assert 'Punto de trabajo estimado' in info.inner_text()
    page.screenshot(path='documentacion/capturas/ficha-bomba-desktop.png', full_page=True)
    page.keyboard.press('Escape')
    assert not info.is_visible()
    page.mouse.click(rect['x'] + rect['width'] * .52, rect['y'] + rect['height'] * .65)
    assert info.is_visible(), 'El clic sobre el cuerpo aislado debe abrir la ficha'
    assert view.get_attribute('data-selected-part') == '183'
    page.locator('#piece').select_option('158')
    assert not info.is_visible()
    page.set_viewport_size({'width':390, 'height':844})
    page.locator('#piece').select_option('183')
    assert info.is_visible(), 'El motor comparte la ficha de la bomba'
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path='documentacion/capturas/ficha-bomba-mobile.png', full_page=True)
    assert not errors, errors
    browser.close()
print('OK: compact pump hover, no selection change, Escape, live state, click and mobile.')
