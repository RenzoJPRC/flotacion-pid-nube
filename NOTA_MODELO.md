# Nota técnica: fuente, modelo y límites

## 1. Fuente primaria

Quintanilla et al. (2023), MethodsX 10, 102081. DOI: 10.1016/j.mex.2023.102081. Documento suministrado por el estudiante. Secciones de referencia: ecuaciones 2, 3 y 5 (SIMC), tabla 2 (identificación y ajuste), ecuaciones 7–9 (PI, feedforward e IAE).

El estudio tiene tres celdas con bombas peristálticas, señales analógicas y control en MATLAB conectado mediante PLC. Su prueba es de nivel, en un sistema agua/aire/reactivos sin sólidos. La implementación del artículo usa PI (Td=0), aunque explica la formulación general PID.

## 2. Modelo seleccionado

Se toman las funciones integradoras finales de la tabla 2:

`G_i(s) = k'_i * exp(-theta_i*s) / s`

Con k' = -0.001018 cm/s/(L/min), y theta = [7,6,3] s. Un incremento de descarga produce pendiente negativa del nivel. Al extender el modelo SISO a un banco acoplado, se supone que el caudal de entrada afecta el nivel con ganancia de signo contrario y sin retardo adicional:

`dh_i/dt = k'_i * (q_salida_i(t-theta_i) - q_entrada_i(t))`

`q_entrada_1 = q_alimentacion_externa`

`q_entrada_2 = q_salida_1(t-theta_1)`

`q_entrada_3 = q_salida_2(t-theta_2)`

Es una **extensión empírica**; los retardos se representan como retardos efectivos de la descarga. No significa que el artículo haya medido por separado ese mecanismo de transporte o actuador. Colas e ingreso aguas abajo utilizan el mismo valor retrasado. No se aplican ambos retardos dos veces.

Se usa Euler explícito: `h[k+1] = h[k] + dt*k'*(q_salida_retrasada - q_entrada)`, con dt=0.1 s. Los retardos se implementan como colas FIFO con N=theta/dt muestras. El historial para las gráficas y CSV se guarda cada 1 s. No existe ruido ni filtrado de sensor que imite artificialmente las mediciones publicadas.

## 3. Por qué no se mezcla el área geométrica con k'

El artículo indica celdas de 300×300 mm: área geométrica 0.09 m² y altura 450 mm. Un balance ideal sin aire daría, expresando nivel en cm y caudal en L/min:

`dh/dt = (q_in-q_out)/(600*A) = (q_in-q_out)/54`

Su ganancia ideal es 0.0185185 cm/s/(L/min), que **no coincide** con el valor identificado 0.001018 de la tabla 2. Esta diferencia no se corrige inventando un área nueva ni se oculta: esta aplicación selecciona el modelo empírico identificado y las ganancias de control asociadas, no el tanque geométrico ideal. No se usa el área para afirmar conservación volumétrica exacta del equipo físico.

No se implementa la recirculación dinámica del tanque externo de 130 litros ni un modelo de espuma/concentrado. La alimentación se impone como señal externa. No se predice recuperación, ley de mineral o eficiencia metalúrgica.

## 4. PI y extensión PID

Convención: `e=SP-h`, por tanto Kc es negativo. En forma posicional:

`q[k] = q0 + Kc*e[k] + I[k] - Kc*Td*d_filtrada(h)[k] + FF[k]`

`I_candidata = I[k-1] + Kc/Ti*e[k]*dt`

Se integra cuando la salida candidata no satura, o cuando el incremento integral favorece salir de saturación. La salida se limita a [0,qmax]. La derivada se aplica a la medición, evitando la patada de consigna, con filtro de primer orden de 1 s. Con Td=0 es PI. El artículo no utilizó un Td distinto de cero; la opción PID es una extensión didáctica, no una ganancia publicada.

Ganancias finales publicadas: Kc=[-62,-76,-85] L/min/cm; Ti=[56,30,44] s. Para comparar con una formulación paralela: Kp=Kc, Ki=Kc/Ti y Kd=Kc*Td, conservando el signo y la derivada sobre medición.

## 5. SIMC y discrepancias de la tabla

Para un integrador puro: `Kc=1/[k'*(tau_c+theta)]`, `Ti=4*(tau_c+theta)`. Los valores tau_c=[7,6,8] s se toman de la tabla, cumpliendo tau_c>=theta.

| Celda | Kc inicial impreso | Ti inicial impreso | Kc recalculado | Ti recalculado | Kc/Ti finales publicados |
|---|---:|---:|---:|---:|---|
| 1 | -70.2 | 56 | -70.1656 | 56 | -62 / 56 |
| 2 | -81.8 | 48 | -81.8599 | 48 | -76 / 30 |
| 3 | -78.1 | 52 | -89.3017 | 44 | -85 / 44 |

La pequeña diferencia de celda 2 puede depender de redondeo o parámetros usados; la de celda 3 no se reproduce con los valores impresos. Se permite seleccionar ganancias finales publicadas o reglas recalculadas. El ajuste experimental final lo realizaron los autores; no se afirma haber realizado esos ensayos físicos en esta práctica.

## 6. Feedforward adaptado

Kff=[0.8,0.8,1.0], según la fuente. La ecuación 8 del artículo utiliza diferencia de caudales de muestras consecutivas. Para esta implementación posicional se adopta explícitamente:

`FF_i=Kff_i*(q_entrada_i-q0)`

Esta compensación de desviación respecto del caudal nominal mantiene una acción ante una perturbación persistente. No es una transcripción literal de la ecuación 8, y por tanto sus resultados no deben citarse como réplica exacta del experimento. No se garantiza mejor IAE en todas las configuraciones, especialmente con Td no nulo, saturación o consignas agresivas.

## 7. Escenario propio y métricas

Nivel inicial=25 cm; q0=45 L/min; consignas iniciales=25 cm. A t=30 s las tres consignas aumentan 1 cm. A t=300 s la alimentación externa aumenta 20%, hasta 54 L/min. Duración=900 s. Son estímulos de diseño propios, no la secuencia experimental de la figura 14.

qmax=100 L/min y límites de nivel 0–39 cm son supuestos de la simulación. No proceden de una calibración de las bombas del artículo. Al tocar límites de nivel se avisa al usuario y se registra `boundary_s`; el recorte no representa un cálculo físico de rebose ni de vaciado.

`IAE = sum(abs(SP-h)*dt)` en cm·s; `ISE=sum((SP-h)^2*dt)` en cm²·s. Se acumulan usando nivel actualizado al final del paso, convención explícita para una suma de Riemann derecha. `saturated_s` registra tiempo de saturación de orden. `boundary_s` registra tiempo en que el nivel libre rebasaría límites.

Los experimentos PI y PI+FF parten de las mismas condiciones. El JSON de referencia se genera ejecutando el código, no digitando resultados esperados ni copiando valores de la figura del artículo.
