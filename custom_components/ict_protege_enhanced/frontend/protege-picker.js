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
  return flow?.domain === DOMAIN && flow?.step?.step_id === STEP_ID;
}

function getFlowForm(flow) {
  return flow?.shadowRoot?.querySelector("ha-form") ?? null;
}

function hideLegacyBulkControls(form) {
  const root = form?.shadowRoot?.querySelector(".root");
  if (!root) {
    return;
  }

  for (const child of root.children) {
    const name = child?.schema?.name ?? child?.name;
    if (name === "select_all" || name === "select_none") {
      child.style.display = "none";
    }
  }
}

function getItemsSelector(flow) {
  const form = getFlowForm(flow);
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

function visibleIds(combo) {
  return (combo?._items ?? [])
    .filter(
      (item) =>
        item &&
        typeof item === "object" &&
        !item.disabled &&
        !String(item.id).startsWith("___")
    )
    .map((item) => String(item.id));
}

function submitFlowData(flow, genericPicker, data) {
  const form = getFlowForm(flow);
  if (!form) {
    return;
  }

  form.data = data;
  flow._stepData = data;
  closePicker(genericPicker);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      flow.submit();
    });
  });
}

function addAllVisible(combo, genericPicker, selector) {
  const flow = findComposedAncestor(selector, "step-flow-form");
  if (!isProtegeScanFlow(flow)) {
    return;
  }

  const ids = visibleIds(combo);
  if (!ids.length) {
    return;
  }

  const form = getFlowForm(flow);
  const current = Array.isArray(form?.data?.items)
    ? form.data.items.map((value) => String(value))
    : [];

  const data = {
    ...(form?.data ?? {}),
    select_all: false,
    select_none: false,
    items: [...new Set([...current, ...ids])],
  };

  submitFlowData(flow, genericPicker, data);
}

function backToScanResults(genericPicker, selector) {
  const flow = findComposedAncestor(selector, "step-flow-form");
  if (!isProtegeScanFlow(flow)) {
    return;
  }

  const form = getFlowForm(flow);
  const data = {
    ...(form?.data ?? {}),
    select_all: false,
    select_none: true,
    items: [],
  };

  submitFlowData(flow, genericPicker, data);
}

function updateToolbar(combo) {
  const bar = combo?.shadowRoot?.querySelector("#ict-protege-picker-actions");
  if (!bar) {
    return;
  }

  const addButton = bar.querySelector("#ict-protege-add-visible");
  const count = visibleIds(combo).length;
  if (addButton) {
    addButton.textContent = count
      ? `Add all visible (${count})`
      : "Add all visible";
    addButton.disabled = count === 0;
  }
}

function installToolbar(combo, genericPicker, selector) {
  if (!combo?.shadowRoot) {
    return;
  }

  let bar = combo.shadowRoot.querySelector("#ict-protege-picker-actions");
  if (!bar) {
    bar = document.createElement("div");
    bar.id = "ict-protege-picker-actions";
    bar.style.cssText = [
      "display:flex",
      "justify-content:space-between",
      "align-items:center",
      "gap:8px",
      "padding:10px 12px 12px",
      "border-top:1px solid var(--divider-color)",
      "background:var(--card-background-color)",
      "flex:0 0 auto",
    ].join(";");

    const backButton = document.createElement("ha-button");
    backButton.setAttribute("appearance", "outlined");
    backButton.textContent = "Back";
    backButton.addEventListener("mousedown", (event) => event.preventDefault());
    backButton.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      backToScanResults(genericPicker, selector);
    });

    const addButton = document.createElement("ha-button");
    addButton.id = "ict-protege-add-visible";
    addButton.setAttribute("appearance", "filled");
    addButton.textContent = "Add all visible";
    addButton.addEventListener("mousedown", (event) => event.preventDefault());
    addButton.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      addAllVisible(combo, genericPicker, selector);
    });

    bar.appendChild(backButton);
    bar.appendChild(addButton);
    combo.shadowRoot.appendChild(bar);

    const search = combo.shadowRoot.querySelector("ha-input-search");
    search?.addEventListener("input", () => {
      requestAnimationFrame(() => updateToolbar(combo));
    });
  }

  updateToolbar(combo);
}

function enhanceSelector(selector, flow) {
  if (!selector?.shadowRoot) {
    return;
  }

  const genericPicker = selector.shadowRoot.querySelector("ha-generic-picker");
  if (!genericPicker) {
    return;
  }

  if (!enhancedSelectors.has(selector)) {
    enhancedSelectors.add(selector);

    genericPicker.addEventListener("picker-opened", () => {
      requestAnimationFrame(() => {
        const combo = genericPicker.shadowRoot?.querySelector(
          "ha-picker-combo-box"
        );
        if (combo) {
          installToolbar(combo, genericPicker, selector);
        }
      });
    });
  }

  if (!autoOpenedFlows.has(flow)) {
    autoOpenedFlows.add(flow);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        genericPicker.open();
      });
    });
  }
}

function enhanceFlow(flow) {
  if (!isProtegeScanFlow(flow)) {
    autoOpenedFlows.delete(flow);
    return;
  }

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

async function install() {
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
    const originalUpdated = FlowElement.prototype.updated;

    FlowElement.prototype.updated = function (...args) {
      const result = originalUpdated?.apply(this, args);
      requestAnimationFrame(() => enhanceFlow(this));
      return result;
    };
  }

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
