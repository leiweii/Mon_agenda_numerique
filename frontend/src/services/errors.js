export const extraireMessageErreur = (error, fallback) => {
  const data = error?.response?.data;

  if (typeof data?.error === 'string' && data.error) {
    return data.error;
  }
  if (typeof data?.detail === 'string' && data.detail) {
    return data.detail;
  }
  if (Array.isArray(data?.non_field_errors) && data.non_field_errors[0]) {
    return data.non_field_errors[0];
  }

  return fallback;
};
