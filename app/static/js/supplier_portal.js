(() => {
  const method = document.getElementById('supplier-method');
  if (!method) return;
  const activity = document.getElementById('activity-fields');
  const factor = document.getElementById('factor-fields');
  const total = document.getElementById('total-fields');
  const sync = () => {
    const value = method.value;
    activity.hidden = value === 'Huella total suministrada' || value === 'Factor por gasto';
    factor.hidden = value === 'Huella total suministrada';
    total.hidden = value !== 'Huella total suministrada';
  };
  method.addEventListener('change', sync);
  sync();
})();
