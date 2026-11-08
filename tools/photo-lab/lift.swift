// lift: cut a person or pet out of a photo using Apple's on-device Vision framework
// (the same "lift subject" technology as the Photos app). Nothing is uploaded.
//
// Usage:
//   lift <input> <output.png> [--mode subject|person] [--instances all|1,2,...] [--mask <mask.png>] [--list]
//
//   --mode subject   people AND animals (default)
//   --mode person    people only (better hair detail for headshots)
//   --instances      which detected subjects to keep (see --list), default all
//   --mask           also save the black/white mask (for manual touch-ups)
//   --list           just print how many subjects were found and their sizes

import CoreImage
import CoreImage.CIFilterBuiltins
import Foundation
import Vision

func fail(_ msg: String) -> Never {
    FileHandle.standardError.write((msg + "\n").data(using: .utf8)!)
    exit(1)
}

var args = Array(CommandLine.arguments.dropFirst())
var mode = "subject", instanceArg = "all", maskPath: String? = nil, listOnly = false
var positional: [String] = []
while !args.isEmpty {
    let a = args.removeFirst()
    switch a {
    case "--mode": mode = args.isEmpty ? mode : args.removeFirst()
    case "--instances": instanceArg = args.isEmpty ? instanceArg : args.removeFirst()
    case "--mask": maskPath = args.isEmpty ? nil : args.removeFirst()
    case "--list": listOnly = true
    default: positional.append(a)
    }
}
guard positional.count >= (listOnly ? 1 : 2) else {
    fail("usage: lift <input> <output.png> [--mode subject|person] [--instances all|1,2] [--mask m.png] [--list]")
}

let inURL = URL(fileURLWithPath: positional[0])
guard let image = CIImage(contentsOf: inURL, options: [.applyOrientationProperty: true]) else {
    fail("Could not open image: \(inURL.path)")
}
let extent = image.extent
let handler = VNImageRequestHandler(ciImage: image, options: [:])
var mask: CIImage

do {
    if mode == "person" {
        let req = VNGeneratePersonSegmentationRequest()
        req.qualityLevel = .accurate
        req.outputPixelFormat = kCVPixelFormatType_OneComponent8
        try handler.perform([req])
        guard let buf = req.results?.first?.pixelBuffer else { fail("No person found.") }
        let m = CIImage(cvPixelBuffer: buf)
        mask = m.transformed(by: CGAffineTransform(scaleX: extent.width / m.extent.width, y: extent.height / m.extent.height))
        if listOnly { print("person mask found"); exit(0) }
    } else {
        let req = VNGenerateForegroundInstanceMaskRequest()
        try handler.perform([req])
        guard let obs = req.results?.first, !obs.allInstances.isEmpty else { fail("No subject found.") }
        if listOnly {
            print("Found \(obs.allInstances.count) subject(s):")
            for i in obs.allInstances.sorted() {
                let buf = try obs.generateScaledMaskForImage(forInstances: IndexSet(integer: i), from: handler)
                let bbox = CIImage(cvPixelBuffer: buf)
                let area = CIFilter.areaAverage()
                area.inputImage = bbox
                area.extent = bbox.extent
                var px = [UInt8](repeating: 0, count: 4)
                CIContext().render(area.outputImage!, toBitmap: &px, rowBytes: 4,
                                   bounds: CGRect(x: 0, y: 0, width: 1, height: 1), format: .RGBA8, colorSpace: nil)
                print("  #\(i): covers about \(Int(Double(px[0]) / 255 * 100))% of the photo")
            }
            exit(0)
        }
        var chosen = obs.allInstances
        if instanceArg != "all" {
            chosen = IndexSet(instanceArg.split(separator: ",").compactMap { Int($0.trimmingCharacters(in: .whitespaces)) })
        }
        let buf = try obs.generateScaledMaskForImage(forInstances: chosen, from: handler)
        mask = CIImage(cvPixelBuffer: buf)
    }
} catch {
    fail("Vision error: \(error.localizedDescription)")
}

let blend = CIFilter.blendWithMask()
blend.inputImage = image
blend.backgroundImage = CIImage(color: .clear).cropped(to: extent)
blend.maskImage = mask
let output = blend.outputImage!.cropped(to: extent)

let ctx = CIContext()
let srgb = CGColorSpace(name: CGColorSpace.sRGB)!
do {
    try ctx.writePNGRepresentation(of: output, to: URL(fileURLWithPath: positional[1]), format: .RGBA8, colorSpace: srgb)
    if let maskPath = maskPath {
        try ctx.writePNGRepresentation(of: mask.cropped(to: extent), to: URL(fileURLWithPath: maskPath), format: .L8, colorSpace: CGColorSpace(name: CGColorSpace.linearGray)!)
    }
} catch {
    fail("Could not save: \(error.localizedDescription)")
}
print("Saved cutout: \(positional[1])")
