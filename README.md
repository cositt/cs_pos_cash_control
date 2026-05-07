# Control de Caja TPV

Modulo Odoo 19 para control de caja por cada Punto de Venta.

## Objetivo

El alcance del modulo es centralizar controles de caja del TPV. Incluye control de fondo fijo de apertura, calculo de efectivo esperado, retirada sugerida, visualizacion de movimientos de efectivo en la pantalla de cierre y ticket impreso con formato de cierre profesional.

La version actual no modifica tickets de cliente, factura, cocina, reservas, permisos generales, ventas, pagos ni impuestos.

## Configuracion

1. Ir a **Punto de Venta > Configuracion > Puntos de venta**.
2. Abrir el TPV deseado.
3. Activar **Control de fondo fijo**.
4. Informar **Fondo fijo de caja**.

La configuracion es independiente por TPV. Por ejemplo, Barra puede tener 250 EUR y Terraza 150 EUR.

## Migracion desde cs_pos_cash_opening_control

Este modulo sustituye a `cs_pos_cash_opening_control`. Si el modulo anterior esta instalado, debe desinstalarse antes de instalar `cs_pos_cash_control` para evitar duplicidades de vistas, assets y definiciones de campos.

Los campos tecnicos existentes se mantienen:

- `cs_fixed_opening_cash_enabled`
- `cs_fixed_opening_cash_amount`

Los campos principales del modulo actual son:

- `cs_fixed_cash_control_enabled`
- `cs_fixed_cash_amount`

## Funcionamiento

- Si el fondo fijo esta activo, el popup de apertura precarga el importe configurado y el campo queda en solo lectura.
- Si alguien intenta abrir la sesion con otro importe desde frontend o RPC/backend, Odoo bloquea la apertura.
- Si el fondo fijo no esta activo, Odoo conserva su comportamiento estandar.
- En el cierre se muestra fondo fijo, apertura real, ventas en efectivo, entradas, salidas, efectivo esperado, retirada sugerida y proximo fondo.
- El boton estandar **Cash In/Out** se abre con **Cash Out**, importe de retirada sugerida y concepto **Retirada cierre de caja** cuando hay retirada pendiente.
- Tambien se muestra el boton **Registrar retirada sugerida**, que registra directamente la salida por el importe pendiente.
- Si el control esta activo y la caja tiene diferencia, no se permite cerrar la sesion. La caja debe cuadrar antes del cierre.
- El boton de imprimir cierre de caja usa una plantilla termica propia de ticket de cierre TPV, con cabecera, apertura/cierre, cobros, ventas por impuestos, informacion adicional, efectivo, entradas/salidas y tarjeta.

Mensaje de bloqueo:

> El fondo de apertura debe ser de 250,00 EUR. No se puede abrir la caja con un importe distinto.

Mensaje de cierre descuadrado:

> No se puede cerrar la caja porque hay una diferencia de 10,00 EUR. La caja debe cuadrar antes de cerrar.

El simbolo y formato de moneda dependen de la configuracion regional/moneda de Odoo.

## Formula

```text
efectivo_esperado_final =
    fondo_apertura
    + ventas_efectivo
    + entradas_efectivo
    + salidas_efectivo

retirada_sugerida =
    max(efectivo_esperado_final - fondo_fijo_configurado, 0)
```

Las salidas de efectivo se almacenan en Odoo con importe negativo, por eso se suman en la formula y reducen el efectivo esperado.

Despues de registrar una salida con concepto **Retirada cierre de caja**, el efectivo esperado baja y la retirada sugerida se recalcula. Si ya no queda importe pendiente, la retirada sugerida pasa a 0.

## Ticket impreso de cierre

La impresion del cierre se genera desde el boton estandar de informe/cierre del TPV, pero el modulo renderiza la plantilla `cs_pos_cash_control.PosCashClosingReport` cuando se imprime una unica sesion.

Se replica con datos reales de Odoo:

- Cabecera de TPV, sesion, empresa, direccion y VAT/CIF.
- Fecha/hora de apertura y usuario de apertura.
- Fecha/hora de cierre y usuario que genera/escribe el cierre.
- Cobros por metodo de pago y total.
- Ventas por impuesto con base, impuesto y total.
- Numero de tickets, facturas, propina y descuentos.
- Comensales y media por comensal si `pos_restaurant` aporta `customer_count`.
- Bloque de efectivo con fondo, ventas, entradas, salidas extraordinarias, esperado, contado, descuadre, retirado y proximo fondo.
- Detalle de entradas/salidas de caja.
- Bloque de tarjeta con numero de transacciones, ventas, propina y total.

Aproximaciones documentadas:

- Usuario de cierre: Odoo no guarda siempre un "cerrado por" operativo independiente; se usa el usuario que escribe/genera el cierre.
- Total contado en efectivo: si hay retirada final registrada, se muestra contado + retirado para poder comparar contra el efectivo esperado antes de retirada, siguiendo la referencia de cierre anterior.
- Retirada final: se identifica por el concepto **Retirada cierre de caja**. Otras salidas se tratan como salidas extraordinarias.
- Tarjeta agrupa todos los metodos no efectivo; si en el TPV existen otros metodos no efectivo, aparecen en cobros totales y se incluyen en ese bloque agregado.

## Pruebas manuales

1. TPV con fondo fijo activado a 250 EUR. Abrir caja con 250 EUR. Debe permitir abrir.
2. TPV con fondo fijo activado a 250 EUR. Intentar abrir con 200 EUR. Debe bloquear y mostrar mensaje claro.
3. Venta en efectivo de 500 EUR sin salidas previas. En cierre debe mostrar retirada sugerida de 500 EUR.
4. Venta en efectivo de 500 EUR con salida previa de 35 EUR. En cierre debe mostrar efectivo esperado de 715 EUR y retirada sugerida de 465 EUR.
5. Pulsar **Cash In/Out** desde cierre. Debe proponer salida, importe de retirada sugerida y concepto **Retirada cierre de caja**.
6. Registrar la retirada sugerida. Debe recalcular retirada sugerida a 0 EUR y proximo fondo a 250 EUR.
7. TPV con control desactivado. Debe funcionar como Odoo estandar.
8. Dos TPV con importes diferentes. Cada TPV debe respetar su importe.
9. Intentar cerrar una sesion con diferencia de caja. Debe bloquear el cierre y mostrar mensaje claro.
10. Imprimir cierre con efectivo y tarjeta. Debe mostrar ambos bloques.
11. Imprimir cierre con salidas previas y retirada final. Debe mostrar el detalle y restar/importar correctamente.
12. Imprimir cierre con impuestos. Debe mostrar base, impuesto y total.
13. Imprimir cierre con comensales. Si existe `customer_count`, debe mostrar comensales y media por comensal.
14. Actualizar el modulo. No debe romper sesiones existentes ni modificar tickets de venta.

## Limitaciones

El bloqueo real obligatorio de apertura esta en backend, en `pos.session._set_opening_control_data`. El bloqueo de cierre descuadrado tambien esta protegido en backend, en `pos.session.post_closing_cash_details`, `pos.session.update_closing_control_state_session` y `pos.session.close_session_from_ui`.

La mejora frontend precarga y bloquea visualmente el popup siempre que el TPV cargue los assets POS actualizados. La plantilla impresa tambien depende de assets POS actualizados. Si el usuario ya tenia el TPV abierto antes de instalar o actualizar el modulo, debe recargar la interfaz del TPV.

El ticket impreso de cierre no cambia la logica fiscal; solo reorganiza la informacion disponible para aproximarla al formato de cierre definido para el TPV.
