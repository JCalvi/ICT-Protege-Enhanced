const DOMAIN = "ict_protege_enhanced";
const STEP_ID = "scan_select";

const enhancedSelectors = new WeakSet();
const autoOpenedFlows = new WeakSet();

function findComposedAncestor(node, tagName) {
  const wanted = tagName.toLowerCase();
  let current = node;

  while (current) {
    if (current.localName === wanted) {
      return current;
    }

    if (current.parentElement) {
      current = current.parentElement;
      continue;
    }

    const root = current.getRootNode?.();
    current = root?.host ?? null;
  }

  return null;
}

function isProtegeScanFlow(flow) {
  return (
    flow?.domain === DOMAIN &&
    flow?.step?.step_id === STEP_ID
  );
}

function hideLegacyBulkControls(form) {
  const root = form?.shadowRoot?.querySelector(".root");
  if (!root) {
    return;
  }

  for (const child of root.children) {
    const name = child?.schema?.name ?? child?.name;
    if (name === "select_all") {
      child.style.display = "none";
    }
  }
}

function getItemsSelector(flow) {
  const form = flow?.shadowRoot?.querySelector("ha-form");
  if (!form?.shadowRoot) {
    return null;
  }

  hideLegacyBulkControls(form);

  const wrappers = form.shadowRoot.querySelectorAll("ha-selector");
  for (const wrapper of wrappers) {
    if (wrapper.name !== "items") {
      continue;
    }

    return wrapper.shadowRoot?.querySelector("ha-selector-select") ?? null;
  }

  return null;
}

function setSelectorValue(selector, values) {
  selector.value = values;
  selector.dispatchEvent(
    new CustomEvent("value-changed", {
      detail: { value: values },
      bubbles: true,
      composed: true,
    })
  );
}

function closePicker(genericPicker) {
  const popover = genericPicker?.shadowRoot?.querySelector("wa-popover");
  if (popover) {
    popover.open = false;
  }

  const bottomSheet = genericPicker?.shadowRoot?.querySelector("ha-bottom-sheet");
  if (bottomSheet) {
    bottomSheet.open = false;
  }
}

function addAllVisible(combo, genericPicker, selector) {
  const visibleIds = (combo?._items ?? [])
    .filter(
      (item) =>
        item &&
        typeof item === "object" &&
        !item.disabled &&
        !String(item.id).startsWith("___")
    )
    .map((item) => String(item.id));

  if (!visibleIds.length) {
    return;
  }

  const current = Array.isArray(selector.value)
    ? selector.value.map((value) => String(value))
    : selector.value
      ? [String(selector.value)]
      : [];

  const values = [...new Set([...current, ...visibleIds])];
  setSelectorValue(selector, values);

  const flow = findComposedAncestor(selector, "step-flow-form");
  if (!isProtegeScanFlow(flow)) {
    return;
  }

  genericPicker.__ictProtegeSubmitting = true;
  closePicker(genericPicker);

  // Allow Home Assistant's form value-changed handlers to update the
  // config-flow step data before submitting it.
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      flow.submit();
    });
  });
}

function installAddAllVisible(combo, genericPicker, selector) {
  if (!combo?.shadowRoot) {
    return;
  }

  let bar = combo.shadowRoot.querySelector("#ict-protege-add-visible");
  if (bar) {
    return;
  }

  bar = document.createElement("div");
  bar.id = "ict-protege-add-visible";
  bar.style.cssText = [
    "display:flex",
    "justify-content:flex-end",
    "align-items:center",
    "gap:8px",
    "padding:10px 12px 12px",
    "border-top:1px solid var(--divider-color)",
    "background:var(--card-background-color)",
    "flex:0 0 auto",
  ].join(";");

  const button = document.createElement("ha-button");
  button.setAttribute("appearance", "filled");
  button.textContent = "Add all visible";
  button.addEventListener("mousedown", (event) => event.preventDefault());
  button.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    addAllVisible(combo, genericPicker, selector);
  });

  bar.appendChild(button);
  combo.shadowRoot.appendChild(bar);
}

function enhanceSelector(selector, flow) {
  if (!selector?.shadowRoot || enhancedSelectors.has(selector)) {
    return;
  }

  const genericPicker = selector.shadowRoot.querySelector("ha-generic-picker");
  if (!genericPicker) {
    return;
  }

  enhancedSelectors.add(selector);

  genericPicker.addEventListener("picker-opened", () => {
    requestAnimationFrame(() => {
      const combo = genericPicker.shadowRoot?.querySelector(
        "ha-picker-combo-box"
      );
      if (combo) {
        installAddAllVisible(combo, genericPicker, selector);
      }
    });
  });

  // Choosing Doors / Areas / Inputs / Outputs should land directly in the
  // searchable result list, matching the original v3.0 interaction.
  if (!autoOpenedFlows.has(flow)) {
    autoOpenedFlows.add(flow);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (!genericPicker.__ictProtegeSubmitting) {
          genericPicker.open();
        }
      });
    });
  }
}

function enhanceFlow(flow) {
  if (!isProtegeScanFlow(flow)) {
    // The same step-flow-form element can be reused as the options flow moves
    // between Scan Results and another record type. Reset the auto-open guard
    // whenever we leave scan_select so the next group opens immediately too.
    autoOpenedFlows.delete(flow);
    return;
  }

  // The searchable picker is the actual interaction. Hide the long backend
  // description so the page does not flash an unnecessary intermediate UI
  // before the picker opens.
  const description = flow.shadowRoot?.querySelector(
    ".content > ha-markdown"
  );
  if (description) {
    description.style.display = "none";
  }

  const selector = getItemsSelector(flow);
  if (selector) {
    enhanceSelector(selector, flow);
  }
}

async function patchComboBoxWhenAvailable() {
  await customElements.whenDefined("ha-picker-combo-box");
  const ComboElement = customElements.get("ha-picker-combo-box");
  if (!ComboElement || ComboElement.prototype.__ictProtegePatched) {
    return;
  }

  ComboElement.prototype.__ictProtegePatched = true;
  const originalComboUpdated = ComboElement.prototype.updated;

  ComboElement.prototype.updated = function (...args) {
    const result = originalComboUpdated?.apply(this, args);
    const flow = findComposedAncestor(this, "step-flow-form");
    if (isProtegeScanFlow(flow)) {
      const genericPicker = findComposedAncestor(this, "ha-generic-picker");
      const selector = findComposedAncestor(this, "ha-selector-select");
      if (genericPicker && selector) {
        requestAnimationFrame(() =>
          installAddAllVisible(this, genericPicker, selector)
        );
      }
    }
    return result;
  };
}

async function install() {
  // Do not wait for ha-picker-combo-box here: it can be lazy-loaded only when
  // a picker first opens. Waiting for it would prevent the automatic open.
  await Promise.all([
    customElements.whenDefined("step-flow-form"),
    customElements.whenDefined("ha-selector-select"),
    customElements.whenDefined("ha-generic-picker"),
  ]);

  const FlowElement = customElements.get("step-flow-form");
  if (!FlowElement) {
    return;
  }

  if (!FlowElement.prototype.__ictProtegePatched) {
    FlowElement.prototype.__ictProtegePatched = true;
    const originalFlowUpdated = FlowElement.prototype.updated;

    FlowElement.prototype.updated = function (...args) {
      const result = originalFlowUpdated?.apply(this, args);
      requestAnimationFrame(() => enhanceFlow(this));
      return result;
    };
  }

  // The combo box is lazy-loaded. Patch it independently as soon as it exists.
  patchComboBoxWhenAvailable();

  // Enhance an already-rendered flow if this module was registered after the
  // dialog had been opened.
  const visit = (root) => {
    for (const element of root.querySelectorAll?.("*") ?? []) {
      if (element.localName === "step-flow-form") {
        enhanceFlow(element);
      }
      if (element.shadowRoot) {
        visit(element.shadowRoot);
      }
    }
  };
  visit(document);
}

install();
