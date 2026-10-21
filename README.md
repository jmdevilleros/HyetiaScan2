*************************************************************************
# HyetiaScan 2.1.2

Análisis de lluvias

- Juan Manuel de Villeros Arias
- Mónica Liliana Gallego Jaramillo

Junio - Agosto 2024

Contacto: hyetiascan@teoktonos.com


*************************************************************************

### Cambios en versión 2.1.2 - Julio 2025

#### Nueva Opción para Controlar la Inclusión de Pausas Iguales a la Pausa Máxima

Se ha añadido una nueva funcionalidad en la interfaz de la pestaña "Eventos" que permite al usuario decidir si las pausas con una duración exactamente igual a la pausa máxima (definida en minutos) se consideran parte de una lluvia continua o como interrupciones que separan eventos de precipitación. 

El usuario puede elegir entre: 
- Incluir (tratar como lluvia): Las pausas de duración igual a la pausa máxima se consideran parte del mismo evento de lluvia (usa <= pausa_maxima).  
- Separar (tratar como interrupción): Las pausas de duración igual a la pausa máxima se tratan como interrupciones que dividen eventos (usa < pausa_maxima).

Este cambio mejora la flexibilidad del análisis de eventos de precipitación, especialmente para casos donde el criterio especificado de pausa máxima es igual al intervalo de medición, permitiendo un control más preciso sobre la definición de eventos continuos. 


---

## Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo [LICENSE](./LICENSE).
