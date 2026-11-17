"""Prueba UI con respuestas serie ficticias interceptadas solo en este navegador."""
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:8001'
with sync_playwright() as p:
    browser = p.chromium.launch(args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':1440, 'height':1100}, reduced_motion='reduce')
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    snapshot = {'conectado':False,'puerto':None,'baudios':None,'error':None,'mensajes_validos':0,'mensajes_invalidos':0,'caducidad_s':5,'lecturas':[]}
    network_error = False
    def route(request):
        path = request.request.url.split(URL)[-1]
        if path == '/api/serie/puertos':
            result = [{'puerto':'COM_PRUEBA','descripcion':'Dispositivo ficticio para pruebas'}]
        elif path == '/api/serie/conectar':
            snapshot.update(conectado=True, puerto='COM_PRUEBA', baudios=115200, mensajes_validos=1)
            snapshot['lecturas'] = [{'pieza':103,'valor':12.3,'unidad':'bar','estado':'vigente','edad_s':0,'recibida_en':datetime.now(timezone.utc).isoformat()}]
            result = snapshot
        elif path == '/api/serie/desconectar':
            snapshot.update(conectado=False, lecturas=[])
            result = snapshot
        elif network_error:
            request.abort(); return
        else:
            result = snapshot
        request.fulfill(json=result)
    page.route('**/api/serie/**', route)
    page.route('**/api/lecturas', route)
    page.goto(URL)
    page.wait_for_selector('#viewport[data-ready="true"]')
    page.locator('#reading-source').select_option('serial')
    assert 'Sin datos actuales' in page.locator('#sensor-reading-102').inner_text()
    page.locator('.serial-settings summary').click()
    page.locator('#serial-port').select_option('COM_PRUEBA')
    page.locator('#serial-connect').click()
    page.wait_for_function('document.getElementById("sensor-reading-102").textContent.includes("12,30")')
    assert 'Sin datos actuales' in page.locator('#sensor-reading-105').inner_text(), 'No completar sensores faltantes con simulación'
    page.locator('[data-sensor-piece="103"]').click()
    assert 'Serie: 12,30 bar' in page.locator('#sensor-live-reading').inner_text()
    page.locator('#pump-toggle').evaluate('(node) => node.click()')
    page.locator('#valve-opening').evaluate('(node) => { node.value=100; node.dispatchEvent(new Event("input")); }')
    assert '12,30' in page.locator('#sensor-reading-102').inner_text(), 'La simulación no debe sobrescribir lecturas recibidas'
    snapshot['lecturas'][0].update(estado='vencida',valor=None,edad_s=6)
    page.wait_for_function('document.getElementById("sensor-range-102").textContent.includes("vencida")')
    assert 'Sin datos actuales' in page.locator('#sensor-reading-102').inner_text()
    snapshot['lecturas'][0].update(estado='vigente',valor=101,edad_s=0)
    page.wait_for_function('document.getElementById("sensor-range-102").textContent.includes("Por encima")')
    network_error = True
    page.wait_for_function('document.getElementById("serial-status").textContent.includes("Sin comunicación")')
    assert 'Sin datos actuales' in page.locator('#sensor-reading-102').inner_text()
    network_error = False
    page.wait_for_function('document.getElementById("sensor-reading-102").textContent.includes("101,00")')
    page.locator('#serial-disconnect').click()
    page.wait_for_function('document.getElementById("sensor-range-102").textContent.includes("desconectado")')
    page.locator('#reading-source').select_option('simulation')
    assert page.locator('#sensor-reading-102').inner_text() != 'Sin datos actuales'
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    page.unroute_all(behavior='wait')
    page.reload(); page.wait_for_selector('#viewport[data-ready="true"]')
    page.locator('#reading-source').select_option('serial')
    page.locator('.serial-settings summary').click()
    page.screenshot(path='documentacion/capturas/arduino-serie-mobile.png',full_page=True)
    browser.close()
print('OK: selección, lectura serie, independencia, caducidad, rangos, desconexión y móvil; hardware ficticio.')
