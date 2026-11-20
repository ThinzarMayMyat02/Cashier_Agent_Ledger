import Foundation
import Vision
import ImageIO
let url = URL(fileURLWithPath: CommandLine.arguments[1])
guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
      let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
      let width = properties[kCGImagePropertyPixelWidth] as? Int,
      let height = properties[kCGImagePropertyPixelHeight] as? Int,
      width > 0, height > 0, width <= 10000, height <= 10000, width * height <= 25000000 else {
    throw NSError(domain: "Invalid or oversized image", code: 1)
}
let text = VNRecognizeTextRequest()
text.recognitionLevel = .accurate
text.recognitionLanguages = ["en-US"]
text.usesLanguageCorrection = false
let qr = VNDetectBarcodesRequest()
qr.symbologies = [.qr]
try VNImageRequestHandler(url: url).perform([text, qr])
let lines = (text.results ?? []).sorted {
    if abs($0.boundingBox.midY - $1.boundingBox.midY) > 0.012 {
        return $0.boundingBox.midY > $1.boundingBox.midY
    }
    return $0.boundingBox.minX < $1.boundingBox.minX
}.compactMap { $0.topCandidates(1).first?.string }

// Read the customer value beside the English label using the Myanmar OCR fallback.
if let label = text.results?.first(where: {
    $0.topCandidates(1).first?.string.range(of: "customer name", options: .caseInsensitive) != nil
}), let image = CGImageSourceCreateImageAtIndex(source, 0, nil) {
    let box = label.boundingBox
    let cropHeight = max(box.height * 4, 0.045)
    let left = min(max(box.maxX + 0.015, 0.35), 0.85)
    let top = max(0, 1 - box.midY - cropHeight / 2)
    let rect = CGRect(x: left * Double(width), y: top * Double(height),
                      width: (0.98 - left) * Double(width),
                      height: min(cropHeight, 1 - top) * Double(height)).integral
    if let crop = image.cropping(to: rect) {
        let output = url.deletingLastPathComponent().appendingPathComponent("customer-name.png")
        if let destination = CGImageDestinationCreateWithURL(output as CFURL, "public.png" as CFString, 1, nil) {
            CGImageDestinationAddImage(destination, crop, nil)
            CGImageDestinationFinalize(destination)
        }
    }
}
let payloads = (qr.results ?? []).compactMap { $0.payloadStringValue }
let result: [String: Any] = ["lines": lines, "qr": payloads]
FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject: result))
