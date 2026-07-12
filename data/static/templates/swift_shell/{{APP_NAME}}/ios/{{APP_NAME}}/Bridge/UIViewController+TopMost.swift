import UIKit

extension UIViewController {
    var {{APP_NAME_LOWER}}TopMost: UIViewController {
        if let presented = presentedViewController {
            return presented.{{APP_NAME_LOWER}}TopMost
        }
        if let nav = self as? UINavigationController, let visible = nav.visibleViewController {
            return visible.{{APP_NAME_LOWER}}TopMost
        }
        if let tab = self as? UITabBarController, let selected = tab.selectedViewController {
            return selected.{{APP_NAME_LOWER}}TopMost
        }
        return self
    }
}
