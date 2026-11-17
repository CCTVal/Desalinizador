"""Llave 167: clic, estado, reparto y corte de descarga sin detener aspersor."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':1440, 'height':1100}, reduced_motion='reduce')
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8001')
    page.wait_for_selector('#viewport[data-ready="true"]')
    view = page.locator('#viewport')
    button = page.locator('#bypass-toggle')
    assert view.get_attribute('data-bypass-open') == 'true'
    assert 'Abierta' in button.inner_text()
    assert button.evaluate('(node) => getComputedStyle(node).opacity') == '0'
    page.locator('#pump-toggle').click()
    page.locator('#valve-opening').evaluate('(node) => {node.value=100; node.dispatchEvent(new Event("input", {bubbles:true}));}')
    opening_pressure = float(view.get_attribute('data-spray-pressure-bar'))
    opening_spray_flow = float(view.get_attribute('data-spray-flow-l-min'))
    assert view.get_attribute('data-water-discharge-reached') == 'true'
    view.focus()
    page.keyboard.press('Tab')
    assert button.evaluate('(node) => getComputedStyle(node).opacity') == '1', 'Disponible con teclado'
    button.click()
    assert view.get_attribute('data-bypass-open') == 'false'
    assert 'Cerrada' in button.inner_text()
    assert float(view.get_attribute('data-bypass-flow-l-min')) == 0
    assert float(view.get_attribute('data-spray-pressure-bar')) > opening_pressure
    assert float(view.get_attribute('data-spray-flow-l-min')) > opening_spray_flow
    assert abs(float(view.get_attribute('data-pump-flow-l-min')) - float(view.get_attribute('data-spray-flow-l-min'))) < 1e-6
    assert view.get_attribute('data-spray-active') == 'true'
    assert view.get_attribute('data-water-discharge-reached') == 'false'
    assert float(view.get_attribute('data-water-drawn-progress')) < 1
    rect = view.bounding_box()
    x, y = rect['x'] + rect['width'] / 2, rect['y'] + rect['height'] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x - rect['height'] * .16, y, steps=6)
    page.mouse.up()
    page.screenshot(path='documentacion/capturas/llave-167-cerrada.png', full_page=True)
    page.locator('#piece').select_option('166')
    view.scroll_into_view_if_needed()
    rect = view.bounding_box()
    hovered = False
    for fx in [.45, .55, .35, .65, .5]:
        for fy in [.35, .65, .45, .75, .55]:
            x, y = rect['x'] + rect['width'] * fx, rect['y'] + rect['height'] * fy
            page.mouse.move(x, y)
            page.wait_for_timeout(40)
            if view.get_attribute('data-valve-hovered') == 'true':
                hovered = True
                break
        if hovered:
            break
    assert hovered, 'El mouse sobre la llave muestra el boton'
    button.hover()
    page.wait_for_timeout(300)
    assert button.evaluate('(node) => getComputedStyle(node).opacity') == '1', 'Se puede llegar al boton'
    page.mouse.move(rect['x'] + 4, rect['y'] + 4)
    page.wait_for_timeout(300)
    assert button.evaluate('(node) => getComputedStyle(node).opacity') == '0', 'Se oculta al salir'
    # Scan only canvas points: verify a CAD click, independently of the HTML label.
    clicked = False
    for fx in [.45, .55, .35, .65, .5]:
        for fy in [.35, .65, .45, .75, .55]:
            x, y = rect['x'] + rect['width'] * fx, rect['y'] + rect['height'] * fy
            if not page.evaluate('([x,y]) => document.elementFromPoint(x,y)?.tagName === "CANVAS"', [x,y]):
                continue
            page.mouse.click(x,y)
            if view.get_attribute('data-bypass-open') == 'true':
                clicked = True
                break
        if clicked:
            break
    assert clicked, 'Pulsar el CAD de la llave debe abrirla'
    assert view.get_attribute('data-selected-part') == '167'
    page.locator('#reset-pieces').click()
    assert view.get_attribute('data-spray-active') == 'true'
    assert view.get_attribute('data-water-discharge-reached') == 'true'
    total = float(view.get_attribute('data-pump-flow-l-min'))
    branches = float(view.get_attribute('data-spray-flow-l-min')) + float(view.get_attribute('data-bypass-flow-l-min'))
    assert abs(total - branches) < 1e-6
    page.set_viewport_size({'width':390, 'height':844})
    # Narrow desktop still supports hover; retain the keyboard alternative.
    view.focus()
    page.keyboard.press('Tab')
    button.click()
    assert view.get_attribute('data-bypass-open') == 'false'
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path='documentacion/capturas/llave-167-mobile.png', full_page=True)
    mobile = browser.new_context(viewport={'width':390, 'height':844}, is_mobile=True, has_touch=True, reduced_motion='reduce')
    touch_page = mobile.new_page()
    touch_page.goto('http://127.0.0.1:8001')
    touch_page.wait_for_selector('#viewport[data-ready="true"]')
    touch_button = touch_page.locator('#bypass-toggle')
    assert touch_button.evaluate('(node) => getComputedStyle(node).opacity') == '1', 'Disponible sin hover en movil'
    touch_button.tap()
    assert touch_page.locator('#viewport').get_attribute('data-bypass-open') == 'false'
    mobile.close()
    assert not errors, errors
    browser.close()
print('OK: valve 167 label and CAD click, pressure increase, flow balance, spray and mobile.')
