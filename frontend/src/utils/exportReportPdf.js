/**
 * Exporta el nodo del informe de predicción a PDF (A4, varias páginas si hace falta).
 * Usa html2canvas + jsPDF para conservar tipografía, markdown renderizado y caracteres Unicode.
 */
import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'

/**
 * @param {HTMLElement} element - Contenedor del informe (p. ej. .report-content-wrapper)
 * @param {string} [filename] - Nombre del archivo .pdf
 */
export async function exportReportElementToPdf(element, filename = 'prediction-report.pdf') {
  if (!element || !(element instanceof HTMLElement)) {
    throw new Error('exportReportElementToPdf: elemento inválido')
  }

  const canvas = await html2canvas(element, {
    scale: 2,
    useCORS: true,
    allowTaint: true,
    logging: false,
    backgroundColor: '#ffffff',
    width: element.scrollWidth,
    height: element.scrollHeight,
    windowWidth: element.scrollWidth,
    windowHeight: element.scrollHeight,
  })

  const imgData = canvas.toDataURL('image/png', 1.0)
  const pdf = new jsPDF({ orientation: 'p', unit: 'mm', format: 'a4' })
  const pageWidth = pdf.internal.pageSize.getWidth()
  const pageHeight = pdf.internal.pageSize.getHeight()
  const imgWidth = pageWidth
  const imgHeight = (canvas.height * imgWidth) / canvas.width

  let heightLeft = imgHeight
  let position = 0

  pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
  heightLeft -= pageHeight

  while (heightLeft > 0) {
    position = heightLeft - imgHeight
    pdf.addPage()
    pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
    heightLeft -= pageHeight
  }

  pdf.save(filename)
}
