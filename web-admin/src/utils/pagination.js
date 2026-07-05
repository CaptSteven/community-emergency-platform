export const unwrapPaginated = data => {
  if (Array.isArray(data)) {
    return {
      list: data,
      total: data.length
    }
  }

  return {
    list: Array.isArray(data?.results) ? data.results : [],
    total: Number(data?.count || 0)
  }
}

export const buildPageParams = pagination => ({
  page: pagination.page,
  page_size: pagination.pageSize
})
