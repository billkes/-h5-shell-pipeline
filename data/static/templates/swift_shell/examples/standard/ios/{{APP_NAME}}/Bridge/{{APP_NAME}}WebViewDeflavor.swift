import ObjectiveC
import UIKit
import WebKit

enum {{APP_NAME}}WebViewDeflavor {
    private static var installed = false

    static func install() {
        guard !installed else { return }
        installed = true
        stripKeyboardAccessoryView()
        swizzleWKWebViewInit()
        swizzleUIViewAddGestureRecognizer()
    }

    static func apply(to webView: WKWebView) {
        let scrollView = webView.scrollView
        scrollView.showsVerticalScrollIndicator = false
        scrollView.showsHorizontalScrollIndicator = false
        scrollView.minimumZoomScale = 1
        scrollView.maximumZoomScale = 1
        scrollView.bouncesZoom = false
        stripDoubleTapGestures(in: scrollView)
    }

    private static func stripKeyboardAccessoryView() {
        guard let contentViewClass = NSClassFromString("WKContentView") else { return }
        let selector = #selector(getter: UIResponder.inputAccessoryView)
        guard let method = class_getInstanceMethod(contentViewClass, selector) else { return }

        let nilAccessory: @convention(block) (AnyObject) -> UIView? = { _ in nil }
        method_setImplementation(method, imp_implementationWithBlock(nilAccessory))
    }

    fileprivate static func stripDoubleTapGestures(in view: UIView) {
        if let gestures = view.gestureRecognizers {
            for gesture in gestures {
                if let tap = gesture as? UITapGestureRecognizer, tap.numberOfTapsRequired == 2 {
                    tap.isEnabled = false
                }
            }
        }
        for subview in view.subviews {
            stripDoubleTapGestures(in: subview)
        }
    }

    private static func swizzleWKWebViewInit() {
        let originalSelector = #selector(WKWebView.init(frame:configuration:))
        let swizzledSelector = #selector(WKWebView.{{APP_NAME_LOWER}}_swizzledInit(frame:configuration:))

        guard
            let originalMethod = class_getInstanceMethod(WKWebView.self, originalSelector),
            let swizzledMethod = class_getInstanceMethod(WKWebView.self, swizzledSelector)
        else { return }

        method_exchangeImplementations(originalMethod, swizzledMethod)
    }

    private static func swizzleUIViewAddGestureRecognizer() {
        let originalSelector = #selector(UIView.addGestureRecognizer(_:))
        let swizzledSelector = #selector(UIView.{{APP_NAME_LOWER}}_swizzledAddGestureRecognizer(_:))

        guard
            let originalMethod = class_getInstanceMethod(UIView.self, originalSelector),
            let swizzledMethod = class_getInstanceMethod(UIView.self, swizzledSelector)
        else { return }

        method_exchangeImplementations(originalMethod, swizzledMethod)
    }
}

private extension WKWebView {
    @objc func {{APP_NAME_LOWER}}_swizzledInit(frame: CGRect, configuration: WKWebViewConfiguration) -> WKWebView {
        let webView = {{APP_NAME_LOWER}}_swizzledInit(frame: frame, configuration: configuration)
        {{APP_NAME}}WebViewDeflavor.apply(to: webView)
        DispatchQueue.main.async {
            {{APP_NAME}}WebViewDeflavor.apply(to: webView)
        }
        return webView
    }
}

private extension UIView {
    @objc func {{APP_NAME_LOWER}}_swizzledAddGestureRecognizer(_ gesture: UIGestureRecognizer) {
        {{APP_NAME_LOWER}}_swizzledAddGestureRecognizer(gesture)
        if let tap = gesture as? UITapGestureRecognizer, tap.numberOfTapsRequired == 2 {
            tap.isEnabled = false
        }
    }
}
