Proyecto COIL interdisciplinario
Big Data y Metodolog�a de la Investigaci�n
Dise�o e implementaci�n de una soluci�n distribuida en la nube para el procesamiento masivo de �rdenes m�dicas en un sistema p�blico de salud

Big Data

Metodolog�a de la Investigaci�n

Reto acad�mico para dise�ar, justificar e implementar una propuesta competitiva ante un comit� evaluador. � Desarrollar desde Metodolog�a de la Investigaci�n una propuesta
innovadora usando componentes t�cnicos para resolver un problema basado en la vida real y lograr un trabajo interdisciplinario � Desarrollar desde Arquitecturas de Big Data, una soluci�n aplicada de los conceptos vistos en el curso

Presentaci�n Ejecutiva

PROYECTO COIL � BIG DATA + METODOLOG�A DE LA INVESTIGACI�N
Contexto del reto
Un gobierno federal desea automatizar el an�lisis de �rdenes m�dicas para decidir cobertura p�blica, porcentaje reconocido y trazabilidad de la decisi�n.
Cada documento incluye fecha, glosa, medio emisor, valor del procedimiento y entidad emisora. La glosa contiene identificaci�n del paciente, edad y medicaci�n asociada al tratamiento. La soluci�n debe clasificar si cubre o no cubre y calcular 100%, 50% o 25% seg�n el perfil del usuario. El comit� valorar� desempe�o t�cnico, metodolog�a de trabajo y costo razonable.

12 millones consultas objetivo < 24 horas
ventana m�xima de procesamiento

Variables cr�ticas de evaluaci�n

Tiempo total

Costo de operaci�n

Escalabilidad

Trazabilidad

La propuesta debe comportarse como una licitaci�n real: s�lida t�cnicamente, sustentada metodol�gicamente y defendible ante un comit�.

0 2

PROYECTO COIL � BIG DATA + METODOLOG�A DE LA INVESTIGACI�N
Planteamiento del problema

Recepci�n
Ingreso del documento desde el sistema fue nte

Extracci�n
Lectura de glosa y datos m�nimos

Clasificaci�n
Determinar si el Estado cubre o no

Cobertura
Calcular 100%, 50% o 25%

Decisi�n
Registrar salida trazable

Campos m�nimos del documento
Fecha
Glosa
Medio emisor Valor del procedimiento Entidad emisora

La glosa concentra la informaci�n cl�nica y administrativa clave para decidir la cobertura.

Estructura de la glosa
Paciente: nombre + identificador DNO + seguro social
Edad del paciente
Medicaci�n o listado de medicamentos Base de decisi�n de cobertura y reconocimiento econ�mico

0 3

PROYECTO COIL � BIG DATA + METODOLOG�A DE LA INVESTIGACI�N
Lo que deben lograr los estudiantes

Prop�sito formativo
Integrar investigaci�n, dise�o t�cnico y an�lisis econ�mico
Investigar y justificar una soluci�n a la medida. Dise�ar arquitectura distribuida y metodolog�a. Defender t�cnicamente el proyecto ante un comit�.

1 Presentaci�n de proyectos
Comunicar con claridad una propuesta t�cnica y acad�mica.
2 Estado del arte
Comparar enfoques existentes y detectar vac�os del mercado.
3 Dise�o econ�mico
Relacionar arquitectura, rendimiento y costo razonable.

4

Competencia t�cnica
Resolver el problema con nube,

procesamiento y almacenamiento

distribuido.

5 Trabajo multidisciplinario
Coordinar perfiles distintos en un contexto COIL e intercultural.

6

Comunicaci�n y m�todo
Usar metodolog�as de desarrollo,

seguimiento y colaboraci�n

geogr�fica.

0 4

PROYECTO COIL � BIG DATA + METODOLOG�A DE LA INVESTIGACI�N
Dos rutas de soluci�n posibles

Opci�n 1
Procesamiento por lotes
Privilegia rendimiento batch para grandes vol�menes y ventanas definidas de ejecuci�n.
Adecuada cuando la meta principal es el tiempo total de corrida. Favorece control de costos por volumen procesado. Exige estrategia robusta de almacenamiento y orquestaci�n.
VMaaloyroer sepfiecriaednocia para cargas masivas repetibles.

Opci�n 2
Ingesta continua e h�brida
Integra recepci�n continua, almacenamiento distribuido y consolidaci�n anal�tica.
Aporta flexibilidad operativa y trazabilidad ampliada. Permite combinar anal�tica, monitoreo y procesamiento diferido. Requiere justificar con claridad el balance costocomplejidad.
VMaaloyroer sflpeexribadiliodad para operaciones continuas y anal�tica posterior.

Ambas opciones deben demostrar escalabilidad, razonabilidad econ�mica y coherencia metodol�gica.
0 5

PROYECTO COIL � BIG DATA + METODOLOG�A DE LA INVESTIGACI�N
Ruta sugerida de trabajo

1
Comprensi�n
Delimitar problema, supuestos y cobertura.

2
Estado del arte
Revisar antecedentes y
soluciones comparables.

3
Formulaci�n
Objetivo, m�todo y criterios de validaci�n.

4
Dise�o t�cnico
A rq uitec tura, flujo de datos y
l�gica.

5

6

Implementaci�n
Prototipo funcional en
AWS con evidencia.

Evaluaci�n
An�lisis e con�m ic o, defensa y cierre.

Fase transversal: coordinaci�n COIL, bit�cora de decisiones, comunicaci�n entre sedes y seguimiento docente por hitos.
0 6

PROYECTO COIL � BIG DATA + METODOLOG�A DE LA INVESTIGACI�N
Entregables esperados

01
Documento de propuesta
25%
del curso
Problema, estado del arte, objetivos, metodolog�a y an�lisis econ�mico.
Formato Word editable

02
Dise�o t�cnico
25%
del curso
Arquitectura distribuida, flujo de datos, l�gica y estrategia de costo.
Diagrama + justificaci�n

Material disponible para el desarrollo: laboratorio de AWS.

03
Implementaci�n
25%
del curso
Prototipo funcional en AWS, pruebas, evidencia y alcance implementado.
C�digo y resultados

04
Presentaci�n final
25%
del curso
Documento consolidado y defensa ejecutiva ante comit� evaluador.
Pitch + defensa oral

0 7

PROYECTO COIL � BIG DATA + METODOLOG�A DE LA INVESTIGACI�N
Esquema de evaluaci�n y r�brica

4 componentes � 25% cada uno

25%
Propuesta metodol�gica

25%
Dise�o t�cnico

25%
Implementaci�n

25%
Documento y presentaci�n

La r�brica se alinea exactamente con los cuatro productos del proyecto.

Propuesta metodol�gica
Problema bien formulado, estado del arte pertinente, objetivos y metodolog�a coherentes.
Soluci�n t�cnica
Arquitectura distribuida clara, l�gica de clasificaci�n defendible y balance costo-rendimiento.
Implementaci�n
Prototipo funcional, uso pertinente de AWS y evidencia de pruebas.
Documento y presentaci�n
Calidad del informe, claridad ejecutiva y defensa convincente ante el comit�.

0 8

