# Convenciones de Diseno de Pantallas

Las tasks de diseno crean mockups finales en Pencil via MCP. No son wireframes — son disenos con la funcionalidad completa, componentes reales de Tailwind, y datos de ejemplo realistas.

---

## 1. Fidelidad: Diseno final

Los disenos deben ser de alta fidelidad funcional:
- Componentes reales: botones, inputs, tablas, modales, tabs, dropdowns, cards, badges, avatars
- Tailwind defaults: paleta de colores por defecto de Tailwind CSS (slate, blue, green, red, amber, etc.)
- Tipografia del sistema: `font-sans` de Tailwind (Inter si esta disponible, sino system-ui)
- Layout real: spacing, padding, border-radius siguiendo la escala de Tailwind (4px base)
- Iconos: usar iconos de Heroicons (outline style) o placeholder reconocible
- Datos de ejemplo realistas: nombres espanoles, emails reales, fechas concretas, estados variados
- Responsive: desktop (1280px) y mobile (375px) para pantallas clave

Lo que NO incluyen:
- Animaciones o transiciones
- Microinteracciones (hover exacto, focus rings)
- Dark mode (roadmap)
- Branding personalizado del tenant (se usa el default de InnaSign)

---

## 2. Design tokens (Tailwind defaults)

### Colores principales
| Uso | Color Tailwind | Hex aproximado |
|-----|---------------|----------------|
| Primary (CTAs, links, acento) | `blue-600` | #2563EB |
| Primary hover | `blue-700` | #1D4ED8 |
| Success | `green-600` | #16A34A |
| Warning | `amber-500` | #F59E0B |
| Danger/Error | `red-600` | #DC2626 |
| Background app | `slate-50` | #F8FAFC |
| Background card | `white` | #FFFFFF |
| Background sidebar | `slate-900` | #0F172A |
| Text primary | `slate-900` | #0F172A |
| Text secondary | `slate-500` | #64748B |
| Text on dark | `white` | #FFFFFF |
| Border | `slate-200` | #E2E8F0 |
| Divider | `slate-100` | #F1F5F9 |

### Tipografia
| Elemento | Clase Tailwind | Tamano |
|----------|---------------|--------|
| H1 (titulo pagina) | `text-2xl font-bold` | 24px |
| H2 (seccion) | `text-xl font-semibold` | 20px |
| H3 (subseccion) | `text-lg font-medium` | 18px |
| Body | `text-sm` | 14px |
| Caption/label | `text-xs text-slate-500` | 12px |
| Button text | `text-sm font-medium` | 14px |

### Spacing
| Uso | Clase | Valor |
|-----|-------|-------|
| Padding de pagina | `p-6` | 24px |
| Gap entre cards | `gap-6` | 24px |
| Padding interno card | `p-4` | 16px |
| Margin entre secciones | `mt-8` | 32px |
| Gap en formularios | `space-y-4` | 16px |

### Border radius
| Elemento | Clase | Valor |
|----------|-------|-------|
| Botones | `rounded-lg` | 8px |
| Cards | `rounded-xl` | 12px |
| Inputs | `rounded-md` | 6px |
| Badges | `rounded-full` | 9999px |
| Modales | `rounded-2xl` | 16px |

### Shadows
| Elemento | Clase |
|----------|-------|
| Card | `shadow-sm` |
| Modal | `shadow-xl` |
| Dropdown | `shadow-lg` |
| Sidebar | ninguna (background solido) |

---

## 3. Componentes estandar

Todos los disenos usan estos componentes consistentemente:

### Botones
| Variante | Apariencia |
|----------|-----------|
| Primary | `bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium` |
| Secondary | `bg-white text-slate-700 border border-slate-300 rounded-lg px-4 py-2` |
| Danger | `bg-red-600 text-white rounded-lg px-4 py-2` |
| Ghost | `text-blue-600 hover:bg-blue-50 rounded-lg px-4 py-2` |
| Icon button | `p-2 rounded-lg text-slate-400 hover:text-slate-600` |
| Disabled | cualquier variante con `opacity-50 cursor-not-allowed` |

### Inputs
| Tipo | Apariencia |
|------|-----------|
| Text input | `border border-slate-300 rounded-md px-3 py-2 text-sm w-full focus:ring-2 focus:ring-blue-500` |
| Con label | label encima: `text-sm font-medium text-slate-700 mb-1` |
| Con error | border `border-red-500`, mensaje debajo: `text-xs text-red-600 mt-1` |
| Textarea | igual que text pero `min-h-[80px]` |
| Select/dropdown | igual que text con chevron a la derecha |
| Checkbox | `h-4 w-4 rounded border-slate-300 text-blue-600` |
| Radio | `h-4 w-4 border-slate-300 text-blue-600` |
| Toggle | switch on/off estilo iOS, `bg-blue-600` cuando activo |

### Tablas
| Elemento | Apariencia |
|----------|-----------|
| Header | `bg-slate-50 text-xs font-medium text-slate-500 uppercase tracking-wider px-4 py-3` |
| Row | `px-4 py-4 text-sm border-b border-slate-100` |
| Row hover | `hover:bg-slate-50` |
| Row selected | `bg-blue-50` |
| Empty state | centrado, icono gris, texto "No hay {items}" + CTA |
| Paginacion | `flex justify-between items-center pt-4` con "Mostrando X-Y de Z" y botones prev/next |

### Cards
| Tipo | Apariencia |
|------|-----------|
| Card basica | `bg-white rounded-xl shadow-sm border border-slate-200 p-4` |
| Card metrica | card basica + numero grande `text-3xl font-bold` + label `text-sm text-slate-500` |
| Card seleccionable | card basica + `ring-2 ring-blue-500` cuando seleccionada |

### Badges / Status
| Estado | Apariencia |
|--------|-----------|
| DRAFT | `bg-slate-100 text-slate-700 text-xs font-medium px-2.5 py-0.5 rounded-full` |
| SENT | `bg-blue-100 text-blue-700` |
| IN_PROGRESS | `bg-amber-100 text-amber-700` |
| COMPLETED | `bg-green-100 text-green-700` |
| DECLINED | `bg-red-100 text-red-700` |
| EXPIRED | `bg-slate-100 text-slate-500` |
| VOIDED | `bg-red-100 text-red-700` |
| SEALING | `bg-purple-100 text-purple-700` + spinner animado |
| SEALING_FAILED | `bg-red-100 text-red-700` + icono warning |

### Modales
| Elemento | Apariencia |
|----------|-----------|
| Overlay | `bg-black/50 fixed inset-0` |
| Container | `bg-white rounded-2xl shadow-xl max-w-lg mx-auto p-6` |
| Titulo | `text-lg font-semibold text-slate-900` |
| Close button | icono X arriba a la derecha |
| Actions | botones alineados a la derecha `flex justify-end gap-3 mt-6` |
| Destructivo | titulo con icono rojo, boton danger en actions |

### Tabs
| Elemento | Apariencia |
|----------|-----------|
| Tab bar | `border-b border-slate-200 flex gap-6` |
| Tab activa | `text-blue-600 border-b-2 border-blue-600 pb-3 text-sm font-medium` |
| Tab inactiva | `text-slate-500 pb-3 text-sm font-medium hover:text-slate-700` |

### Toast / Notificaciones
| Tipo | Apariencia |
|------|-----------|
| Success | `bg-green-50 border-l-4 border-green-500 p-4` con icono check verde |
| Error | `bg-red-50 border-l-4 border-red-500 p-4` con icono X rojo |
| Warning | `bg-amber-50 border-l-4 border-amber-500 p-4` con icono warning |
| Info | `bg-blue-50 border-l-4 border-blue-500 p-4` con icono info |

---

## 4. Layouts

### Dashboard Layout
```
+----------------------------------------------------------+
| Sidebar (240px)  |  Main Content                          |
| bg-slate-900     |  bg-slate-50                           |
|                  |                                        |
| [Logo]           |  Topbar: breadcrumb + user menu        |
| ─────────        |  ─────────────────────────────────      |
| Nav items:       |                                        |
|  Inicio          |  Content area (max-w-7xl mx-auto p-6)  |
|  Sobres          |                                        |
|  Plantillas      |                                        |
|  Contactos       |                                        |
|  Grupos          |                                        |
|  Sellado         |                                        |
|  ─────────       |                                        |
|  Developer       |                                        |
|  Settings        |                                        |
|  ─────────       |                                        |
|  [User avatar]   |                                        |
|  Nombre          |                                        |
|  Plan: Starter   |                                        |
+----------------------------------------------------------+
```

Sidebar responsive:
- Desktop (>= 1024px): sidebar fija visible
- Tablet (768-1023px): sidebar colapsable (solo iconos, expand on hover)
- Mobile (< 768px): sidebar oculta, hamburger menu en topbar

### Signer Workspace Layout
```
+----------------------------------------------------------+
| Topbar: Logo InnaSign (o logo tenant) | Idioma | Progreso |
+----------------------------------------------------------+
|                                                           |
|  [PDF Document Viewer - area central]                     |
|                                                           |
|  +--- Campo interactivo ---+                              |
|  | [Click para firmar]     |                              |
|  +-------------------------+                              |
|                                                           |
+----------------------------------------------------------+
| Bottom bar: [< Anterior]  Paso X de Y  [Siguiente >]     |
+----------------------------------------------------------+
```

Mobile-first: el viewer ocupa todo el ancho, bottom bar fija, campos interactivos con tamanio minimo tactil (44x44px).

---

## 5. Cuando crear una task de diseno

Crear task de diseno para:
- Paginas completas nuevas del Dashboard (home, listados, detalle, wizard, settings)
- Paginas del Signer Workspace (entry, auth, firma, completado, error)
- Componentes complejos reutilizables (PDF viewer, canvas de firma, editor de campos)
- Modales con formularios significativos (crear webhook, delegacion, sellado directo)

NO crear task de diseno para:
- Integraciones API sin UI (stores, composables, API calls)
- Tasks de backend
- Componentes triviales derivados de los componentes estandar
- Configuraciones (middleware, routing)

---

## 6. Estados alternativos a disenar

Solo disenar estados alternativos cuando son visualmente MUY distintos del default:

| Pantalla | Estado alternativo | Por que |
|----------|-------------------|---------|
| Listado de sobres | Empty state | Call to action "Crea tu primer sobre" con ilustracion |
| Home Dashboard | Sin datos | Primer uso, metricas en cero, onboarding cards |
| Signer: Expirado | Error page | Pantalla completa distinta, sin PDF viewer |
| Signer: Token invalido | Error page | Pantalla completa distinta |
| Signer: Ya firmado | Info page | Pantalla de "ya has firmado este documento" |

Para el resto de pantallas, solo se disena el estado default con datos.

---

## 7. Estructura en Pencil

Las pantallas se organizan en los ficheros Pencil existentes:

### wireframes-dashboard.pen
```
EP06 - Auth/
  Login [Desktop]
  Login [Mobile]
  Forgot Password [Desktop]
  Reset Password [Desktop]

EP12 - Wizard/
  Step 1 - Documents [Desktop]
  Step 1 - Documents [Mobile]
  Step 2 - Recipients [Desktop]
  Step 2 - Recipients [Mobile]
  Step 3 - Fields Editor [Desktop]
  Step 3 - Fields Editor [Mobile]
  Step 4 - Config [Desktop]
  Step 5 - Review [Desktop]
  Step 5 - Review [Mobile]

EP17 - Seal/
  Sellado Directo [Desktop]

EP21 - Dashboard/
  Home [Desktop]
  Home [Mobile]
  Home - Empty State [Desktop]
  Envelope List [Desktop]
  Envelope List [Mobile]
  Envelope List - Empty State [Desktop]
  Envelope Detail [Desktop]
  Envelope Detail [Mobile]

EP22 - Templates Groups/
  Template List [Desktop]
  Contact List [Desktop]
  Signing Group CRUD [Desktop]

EP23 - Developer Hub/
  API Keys [Desktop]
  Webhooks [Desktop]
  Webhook Create Modal [Desktop]

EP24 - SDK/
  Allowed Origins Settings [Desktop]

EP25 - Settings/
  General [Desktop]
  Branding [Desktop]
  Legal Pages [Desktop]
```

### wireframes-signer.pen
```
EP13 - Session/
  Entry Loading [Desktop]
  Entry Loading [Mobile]
  PDF Viewer con campos [Desktop]
  PDF Viewer con campos [Mobile]
  Navegacion guiada [Mobile]
  Completado [Desktop]
  Completado [Mobile]
  Rechazo con motivo [Desktop]
  Rechazo con motivo [Mobile]
  Expirado - Error [Desktop]
  Expirado - Error [Mobile]
  Token invalido - Error [Mobile]
  Ya firmado - Info [Mobile]

EP14 - Auth/
  OTP Input [Desktop]
  OTP Input [Mobile]
  Access Code Input [Mobile]

EP15 - Firma/
  Canvas biometrico [Desktop]
  Canvas biometrico [Mobile]
  Firma mecanografiada [Mobile]
  Upload imagen [Mobile]
  Selector modo firma [Mobile]
  Consentimiento biometrico [Mobile]
  Reviewer vista solo lectura [Desktop]
  Reviewer vista solo lectura [Mobile]
```

### Naming de paginas
```
{EPxx} - {Area} / {Pantalla} [{Variante}]
```

---

## 8. Que incluir en cada diseno

Cada pantalla debe mostrar:

1. **Layout completo**: sidebar/topbar (si aplica), content area, footer (si aplica)
2. **Todos los elementos interactivos**: botones, inputs, dropdowns, checkboxes, toggles — con labels reales
3. **Datos de ejemplo realistas**:
   - Nombres: "Maria Garcia Lopez", "Carlos Fernandez Ruiz"
   - Emails: "maria.garcia@acme.es", "carlos@logistica.com"
   - Empresas: "Acme Transportes S.L.", "Logistica del Sur S.A."
   - Documentos: "Contrato de alquiler 2026.pdf", "Anexo condiciones.pdf"
   - Fechas: "10 abr 2026", "hace 2 horas"
   - Estados variados en listados (mezcla de DRAFT, SENT, COMPLETED, etc.)
4. **Jerarquia visual**: que es lo mas importante en la pagina, que es secundario
5. **Anotaciones en Pencil**: notas para interacciones no obvias (ej: "este dropdown filtra la tabla", "este boton abre modal de confirmacion")

---

## 9. Template de task de diseno

Las tasks de diseno tienen un formato especial distinto de las tasks de codigo:

```markdown
# T{xx}.{y}.0 — Diseno: {descripcion}

> **Story:** S{xx}.{y} | **Epic:** EP{xx} | **Fase:** F{n} | **Story Points:** {pts}
> **Depende de:** ninguna (siempre es la primera task de frontend de la story)
> **Tipo:** Diseno

## Seguimiento
| Campo | Valor |
|-------|-------|
| Estado | pendiente |
| Asignado | — |
| ... |

## Descripcion
Crear disenos finales en Pencil para {descripcion de las pantallas}.

## Pantallas a crear

| Pagina en Pencil | Variantes | Fichero |
|-----------------|-----------|---------|
| EP{xx} - {Area} / {Pantalla} | Desktop, Mobile | wireframes-{app}.pen |

## Detalle por pantalla

### {Pantalla 1}

**Layout:** {Dashboard layout / Signer layout / fullscreen / modal}

**Elementos:**
- Header: {descripcion}
- Seccion principal: {descripcion detallada de cada elemento}
  - {Componente}: {tipo de componente estandar} — {contenido/label}
  - {Componente}: {tipo} — {contenido}
- Acciones: {botones, su posicion, su variante (primary/secondary/danger)}
- Footer/bottom bar: {si aplica}

**Datos de ejemplo:**
- {Campo}: "{valor de ejemplo realista}"
- {Campo}: "{valor}"

**Interacciones clave (anotaciones):**
- {Elemento} → {que pasa al hacer click/hover/focus}
- {Elemento} → {que pasa}

### {Pantalla 2 — si aplica estado alternativo}
{...}

## Criterios de aceptacion
- [ ] Todas las pantallas creadas en {fichero}.pen
- [ ] Variantes desktop ({ancho}px) y mobile (375px) donde se indica
- [ ] Componentes usan el design system de InnaSign (colores, tipografia, spacing de Tailwind defaults)
- [ ] Datos de ejemplo realistas (no lorem ipsum, no "test")
- [ ] Jerarquia visual clara: CTA principal destacado
- [ ] Anotaciones para interacciones no obvias
```

---

## 10. Inventario completo de pantallas

### Dashboard: 28 pantallas (incluyendo variantes)

| # | Pantalla | Variantes | Story |
|---|----------|-----------|-------|
| 1 | Login | Desktop, Mobile | S06.5 |
| 2 | Forgot Password | Desktop | S06.5 |
| 3 | Reset Password | Desktop | S06.5 |
| 4 | Gestion de Usuarios + Invitaciones | Desktop | S06.7 |
| 5 | Aceptacion de invitacion (publica) | Desktop | S06.7 |
| 6 | Wizard Step 1 - Documents | Desktop, Mobile | S12.3 |
| 7 | Wizard Step 2 - Recipients | Desktop, Mobile | S12.3 |
| 8 | Wizard Step 3 - Fields Editor | Desktop, Mobile | S12.3 |
| 9 | Wizard Step 4 - Config | Desktop | S12.3 |
| 10 | Wizard Step 5 - Review | Desktop, Mobile | S12.3 |
| 11 | Sellado Directo | Desktop | S17.2 |
| 12 | Home (metricas) | Desktop, Mobile | S21.1 |
| 13 | Home - Empty State | Desktop | S21.1 |
| 14 | Envelope List | Desktop, Mobile | S21.2 |
| 15 | Envelope List - Empty State | Desktop | S21.2 |
| 16 | Envelope Detail | Desktop, Mobile | S21.3 |
| 17 | Template List | Desktop | S22.1 |
| 18 | Contact List | Desktop | S22.2 |
| 19 | Signing Group CRUD | Desktop | S22.3 |
| 20 | Developer Hub - API Keys | Desktop | S23.4 |
| 21 | Developer Hub - Webhooks | Desktop | S23.4 |
| 22 | Webhook Create Modal | Desktop | S23.1 |
| 23 | Allowed Origins (SDK) | Desktop | S24.3 |
| 24 | Settings - General | Desktop | S25.1 |
| 25 | Settings - Branding | Desktop | S25.1 |
| 26 | Legal Pages | Desktop | S25.5 |
| 27 | Share Link Modal | Desktop | S25.4 |
| 28 | Workspace Switcher + Settings | Desktop | S07.4 |

### Signer Workspace: 20 pantallas (incluyendo variantes)

| # | Pantalla | Variantes | Story |
|---|----------|-----------|-------|
| 1 | Entry Loading | Desktop, Mobile | S13.1 |
| 2 | PDF Viewer con campos | Desktop, Mobile | S13.2 |
| 3 | Navegacion guiada | Mobile | S13.2 |
| 4 | Completado | Desktop, Mobile | S13.3 |
| 5 | Rechazo con motivo | Desktop, Mobile | S13.3 |
| 6 | Expirado - Error | Desktop, Mobile | S13.3 |
| 7 | Token invalido - Error | Mobile | S13.3 |
| 8 | Ya firmado - Info | Mobile | S13.3 |
| 9 | Re-auth modal | Mobile | S13.4 |
| 10 | OTP Input | Desktop, Mobile | S14.2 |
| 11 | Access Code Input | Mobile | S14.4 |
| 12 | Canvas biometrico | Desktop, Mobile | S15.1 |
| 13 | Firma mecanografiada | Mobile | S15.2 |
| 14 | Upload imagen firma | Mobile | S15.2 |
| 15 | Selector modo firma (tabs) | Mobile | S15.2 |
| 16 | Consentimiento biometrico | Mobile | S15.1 |
| 17 | Reviewer vista solo lectura | Desktop, Mobile | S15.3 |

**Total: ~48 pantallas con variantes**
